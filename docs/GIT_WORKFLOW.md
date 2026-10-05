# 팀 Git 협업 방식

대상 저장소는 `HanhwaAcademy-Team-One/ontology-product-system`이며, 검토 담당 계정은 `Isaac0424`입니다.

**적용 상태:** 현재는 로컬 설정안입니다. GitHub 공개 전환·Ruleset 적용·main의 CODEOWNERS 업로드를 완료해야 실제로 동작합니다. 로컬 JSON과 CODEOWNERS 파일만으로 GitHub 권한이 바뀌지는 않습니다.

**목표 권한**

| 사용자 | 작업 브랜치 개발·푸시 | main 직접 푸시 | main으로 PR 병합 |
| --- | --- | --- | --- |
| Isaac0424 | 가능 | 가능 | 본인이 검토 후 병합 |
| 팀원, 저장소 Write 권한 필요 | 가능 | 차단 | PR 제출 후 Isaac0424가 검토·병합 |

main에만 두 Ruleset을 적용합니다. 작업 브랜치는 이 규칙의 대상이 아닙니다.

- `main-owner-and-pull-requests`: main 생성·갱신을 제한하고 PR 검토를 요구합니다. 예외는 사용자 ID `95865694`의 `Isaac0424` 한 명입니다. Admin·Write 역할 전체나 팀·앱은 예외에 넣지 않습니다.
- `main-history-protection`: main 삭제와 force push를 모든 사용자에게 차단합니다. 본인의 정상 푸시는 유지하면서 기록 덮어쓰기·삭제도 막기 위해 별도 규칙으로 만듭니다.
- `.github/CODEOWNERS`: 전체 파일의 검토 담당자로 `@Isaac0424`를 지정합니다. PR의 대상인 main 브랜치에 있어야 검토 요청에 적용됩니다.

Isaac0424는 직접 푸시가 필요한 담당자이므로 첫 번째 규칙의 PR 요구에도 예외입니다. 본인은 PR을 우회해 푸시·병합할 수 있으며, 팀원 PR은 본인이 내용을 확인하고 승인·병합하는 방식으로 운영합니다. PR에 새 변경이 추가되면 기존 승인을 다시 받도록 설정합니다.

저장소나 조직의 설정 관리 권한을 가진 사람은 규칙 자체를 변경할 수 있습니다. 팀원에게는 보통 Write를 부여하고, 관리 권한을 별도로 주지 않아야 이 운영 방식이 유지됩니다.

**팀원의 작업 순서**

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/parser
# 담당 기능 구현·테스트
git add -- src/ontoproduct/agents/parser_agent.py tests/test_real_parser.py
git commit -m "feat: add real document parser"
git push -u origin feature/parser
```

위 add 명령은 해당 신규 파일을 만든 뒤 사용하는 예시입니다. 본인이 실제로 수정한 파일을 선택하세요. GitHub에서 `feature/parser → main` PR을 열고 변경 내용과 테스트 결과를 작성합니다. Isaac0424가 검토 의견을 남기면 같은 브랜치에서 수정·푸시합니다. 검토가 끝나면 Isaac0424가 병합합니다.

**설정 후 확인할 동작**

1. 저장소가 Public이며 두 Ruleset이 Active인지 확인합니다. 비공개 조직 Free 저장소에서는 규칙이 강제되지 않습니다.
2. 첫 번째 규칙의 유일한 예외가 Isaac0424인지 확인합니다.
3. 팀원은 feature 브랜치에 푸시할 수 있고, main 직접 푸시·병합은 차단되는지 팀원 계정으로 확인합니다.
4. 팀원 PR에 Isaac0424가 코드 소유자로 지정되는지 확인합니다.
5. 본인이 PR 검토·병합과 main 정상 푸시를 할 수 있는지 확인합니다.
6. main의 force push·삭제는 차단되는지 규칙으로 확인합니다. 실제 main 기록을 덮어쓰거나 삭제하는 테스트는 하지 않습니다.

공식 참고: [Ruleset 만들기](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository), [Rules API](https://docs.github.com/en/rest/repos/rules), [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).
