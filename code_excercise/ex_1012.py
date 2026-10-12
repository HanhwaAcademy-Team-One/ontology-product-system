import requests # 도구 사용 선언

OLLAMA_URL = "http://localhost:11434/api/generate"

def llama_test_prompt(MODEL, technique_naem, prompt): # 함수 + 매개변수 정의
    print(f"\n{"="*20} {technique_naem} {"="*20}")
    response = requests.post(
        OLLAMA_URL,
        json={ # json이라는 형식으로 포장해서 보내주세요
            "model": MODEL, # 이 모델로 답해주세요
            "prompt": prompt, # 질문은 이거에요
            "stream": False # 스트림 방식으로 출력하지 않을거에요(한 번에 답 받기)
        }
    )
    print(response.json()["response"])
    # response.json() - 받은 답은 파이썬이 읽을 수 있는 json 형태로 바꾸고
    # ["response"] - 그 안에서 "AI의 답변 글자" 부분만 꺼내요

# 식당 주문 비유
# Ollama = 내 노트북 안에 있는 주방(AI)
# OLLAMA_URL = 주방의 주문 창구 주소
# 함수 = 주문서를 써서 창구에 넣고, 나온 음식을 받아 오는 심부름 담당

# 테스트 출력 (예시)
llama_test_prompt("올라마 모델", "Zero-shot/Few-shot/CoT", "프롬프트 이름")
# 값(인자)을 위에서 정의한 매개변수 자리에 넘겨줘서 출력

# 변수를 정의하고, 인자로 넘겨 함수 호출
# 예시
test_model = "exaone3.5"
llama_test_prompt(test_model, "Zero-shot/Few-shot/CoT", "프롬프트 이름")

# ----------------------------------------------------------------------

import openai

client = openai.OpenAI(
# client(변수)/openai.OpenAI(openai 안에 있는 OpenAI)
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)
# 전화기 비유: base_url (전화를 어디로 걸지)/api_key(인증 열쇠)

response = client.chat.completions.create( # client의 chat 기능에서, completions 메뉴로 들어가서, 답변을 새로 만들어줘(create)
    model="llama3.1", # 어떤 모델에게 물을지
    messages=[ 
        {"role": "user", "content": "Hello! Please introduce yourself!"}
    ]   # messages: 질문 내용/role: 누가 말했는지/content: 무슨 말인지 
)

print(response.choices[0].message.content)
# 답장에서 답변 글자만 꺼내서 화면에 보여줘요
# choices[0]: 답변 후보 중 첫 번째예요. (컴퓨터는 0부터 세요.)
# .message.content: 그 안의 메시지에서 글자 내용만 꺼내요.