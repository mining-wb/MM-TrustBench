import re
from typing import Dict, Any

#======配置区======
# 让模型按这三段输出，方便正则抠
EVIDENCE_HEAD = "Evidence:"
SELF_CHECK_HEAD = "Self-check:"
ANSWER_HEAD = "Answer:"


#======证据+自检流水线======
class TrustPipeline:
    """
    在裸模型之上加一层「证据 + 自检」：先让模型说看到了啥、再自检能否答，最后才给 yes/no。
    若自检说不支持或答 Unsupported，则拒答，不强行给 yes/no。
    """

    def __init__(self, wrapper) -> None:
        """
        wrapper 需有 predict(image_path: str, question: str) -> str。
        """
        self.wrapper = wrapper

    def _build_prompt(self, question: str) -> str:
        """
        拼成带指令的完整 prompt，要求模型按 Evidence / Self-check / Answer 三段输出。
        """
        return (
            "Follow this format exactly.\n"
            "1) Evidence: Briefly describe what you see in the image relevant to the question.\n"
            "2) Self-check: Does the evidence support a clear yes/no answer? "
            "If you are uncertain or the image does not show enough, say Unsupported.\n"
            "3) Answer: Give only one word: yes, no, or Unsupported.\n\n"
            f"Question: {question}\n\n"
            "Evidence:\n"
            "Self-check:\n"
            "Answer:"
        )

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """
        从模型回复里抠 Evidence、Self-check、Answer。
        若解析不到或 Answer 为 Unsupported，则 answer 置为 refused。
        """
        evidence = ""
        self_check = ""
        answer = "refused"

        if not raw or raw.strip() == "Error":
            return {"answer": "refused", "evidence": evidence, "self_check": self_check, "raw": raw or ""}

        text = raw.strip()
        # 不区分大小写，按段抠
        ev_match = re.search(r"Evidence:\s*(.*?)(?=Self-check:|$)", text, re.DOTALL | re.IGNORECASE)
        if ev_match:
            evidence = ev_match.group(1).strip()
        sc_match = re.search(r"Self-check:\s*(.*?)(?=Answer:|$)", text, re.DOTALL | re.IGNORECASE)
        if sc_match:
            self_check = sc_match.group(1).strip()
        ans_match = re.search(r"Answer:\s*(\w+)", text, re.IGNORECASE)
        if ans_match:
            a = ans_match.group(1).strip().lower()
            if a == "yes":
                answer = "yes"
            elif a == "no":
                answer = "no"
            # else 保持 refused（含 Unsupported 或乱写）

        # 自检里明确说不支持，或 Answer 段不是 yes/no，都算拒答
        if answer not in ("yes", "no"):
            answer = "refused"
        elif "unsupported" in self_check.lower():
            answer = "refused"

        return {"answer": answer, "evidence": evidence, "self_check": self_check, "raw": raw}

    def process(self, image_path: str, question: str) -> Dict[str, Any]:
        """
        入口：拼 prompt → 调 wrapper → 解析三段 → 返回 answer（yes/no/refused）、evidence、self_check、raw。
        """
        prompt = self._build_prompt(question)
        raw = self.wrapper.predict(image_path, prompt)
        return self._parse_response(raw)


#======自测======
if __name__ == "__main__":
    import sys
    import os
    _src = os.path.dirname(os.path.abspath(__file__))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    from wrapper import ModelWrapper

    wrapper = ModelWrapper()
    pipeline = TrustPipeline(wrapper)
    out = pipeline.process(
        "data/images/COCO_val2014_000000210789.jpg",
        "Is there a person in the image?",
    )
    print(out)
