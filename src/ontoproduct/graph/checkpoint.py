from langgraph.checkpoint.memory import InMemorySaver


def memory_checkpointer():
    return InMemorySaver()
