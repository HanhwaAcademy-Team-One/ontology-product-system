import sqlite3
from threading import Lock
from uuid import UUID, uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from ontoproduct.agents.duplicate_agent import DuplicateAgent
from ontoproduct.agents.registration_agent import RegistrationAgent
from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.mocks.agents import mock_registry
from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.repositories.registration_repository import RegistrationRepository
from ontoproduct.services.document_service import DocumentService
from ontoproduct.services.duplicate_service import DuplicateService
from ontoproduct.services.ontology_service import OntologyService
from ontoproduct.services.registration_service import RegistrationService


class WorkflowRuntime:
    def __init__(self, paths, *, registry_factory=None):
        self.paths = paths
        database = Database(paths.product_db)
        self.products = ProductRepository(database)
        self.cases = RegistrationRepository(database)
        self.documents = DocumentService(paths.uploads)
        self.ontology = OntologyService()
        self.registration = RegistrationService(
            self.products, self.ontology, paths.exports
        )
        paths.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(
            paths.checkpoint_db, check_same_thread=False, timeout=30
        )
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.checkpointer = SqliteSaver(
            self.connection, serde=JsonPlusSerializer(allowed_msgpack_modules=[])
        )
        self.registry_factory = registry_factory or mock_registry
        self._graphs, self._locks, self._registries = {}, {}, {}
        self._guard = Lock()

    @staticmethod
    def config(thread_id):
        return {
            "configurable": {"thread_id": str(UUID(thread_id))},
            "recursion_limit": 150,
        }

    def graph(self, thread_id):
        thread_id = str(UUID(thread_id))
        with self._guard:
            if thread_id not in self._graphs:
                registry = self.registry_factory(self.ontology)
                registry.register(RegistrationAgent(thread_id, self.registration), replace=True)
                registry.register(DuplicateAgent(DuplicateService(self.products, self.ontology)), replace=True)
                self._registries[thread_id] = registry
                self._graphs[thread_id] = build_workflow(
                    registry, ontology=self.ontology, checkpointer=self.checkpointer
                )
                self._locks[thread_id] = Lock()
            return self._graphs[thread_id]

    def create_case(self, session_id):
        session_id = str(UUID(session_id))
        thread_id = str(uuid4())
        self.cases.create(thread_id, session_id)
        return thread_id

    def snapshot(self, thread_id):
        return self.graph(thread_id).get_state(self.config(thread_id))

    def start(
        self, thread_id, references, *, max_extraction_retries=1, max_ontology_retries=1
    ):
        self.documents.validate_references(references)
        case = self.cases.get(thread_id)
        if not case:
            raise ValueError("Unknown registration case")
        state = initial_state(
            references,
            case_id=thread_id,
            max_extraction_retries=max_extraction_retries,
            max_ontology_retries=max_ontology_retries,
        )
        state["session_id"] = case["session_id"]
        yield from self._stream(thread_id, state, starting=True)

    def resume(self, thread_id, payload):
        yield from self._stream(thread_id, Command(resume=payload), starting=False)

    def continue_run(self, thread_id):
        yield from self._stream(thread_id, None, starting=False, continuing=True)

    def _stream(self, thread_id, request, *, starting, continuing=False):
        graph = self.graph(thread_id)
        lock = self._locks[thread_id]
        if not lock.acquire(blocking=False):
            raise ValueError("This registration case is already running")
        try:
            snapshot = graph.get_state(self.config(thread_id))
            if starting and snapshot.values:
                raise ValueError(
                    "This case has already started; resume the saved checkpoint"
                )
            interrupted = any(task.interrupts for task in snapshot.tasks)
            if continuing:
                if interrupted or not (snapshot.next or snapshot.tasks):
                    raise ValueError(
                        "This case has no unfinished execution to continue"
                    )
            elif not starting and not interrupted:
                if snapshot.values.get("case_status") == "REGISTERED":
                    yield (
                        "custom",
                        {
                            "event": "case_already_registered",
                            "status": "ALREADY_REGISTERED",
                        },
                    )
                    return
                raise ValueError("This case is not waiting for a review command")
            yield from graph.stream(
                request, self.config(thread_id), stream_mode=["custom", "updates"]
            )
        finally:
            try:
                snapshot = graph.get_state(self.config(thread_id))
                if snapshot.values:
                    status = (
                        "ERROR"
                        if any(
                            i.value.get("kind") == "error"
                            for t in snapshot.tasks
                            for i in t.interrupts
                        )
                        else snapshot.values["case_status"]
                    )
                    self.cases.update_status(thread_id, status)
            finally:
                lock.release()

    def agent_metadata(self, thread_id=None):
        if thread_id:
            self.graph(thread_id)
            return self._registries[thread_id].metadata()
        registry = self.registry_factory(self.ontology)
        registry.register(RegistrationAgent("metadata", self.registration), replace=True)
        registry.register(DuplicateAgent(DuplicateService(self.products)), replace=True)
        return registry.metadata()

    def compiled_diagram(self):
        return build_workflow(ontology=self.ontology).get_graph().draw_mermaid()

    def close(self):
        self.connection.close()
