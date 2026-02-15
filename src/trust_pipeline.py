import re
from typing import Dict, Any

#======配置区======
# 让模型按这三段输出，正则按这个抠
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
            f"{EVIDENCE_HEAD}\n"
            f"{SELF_CHECK_HEAD}\n"
            f"{ANSWER_HEAD}"
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
        # 不区分大小写，按段抠，用配置区的常量拼正则
        ev_pat = re.escape(EVIDENCE_HEAD) + r"\s*(.*?)(?=" + re.escape(SELF_CHECK_HEAD) + r"|$)"
        ev_match = re.search(ev_pat, text, re.DOTALL | re.IGNORECASE)
        if ev_match:
            evidence = ev_match.group(1).strip()
            # 模型有时在段末加 "2)" "3)"，顺手去掉
            evidence = re.sub(r"\n+\s*\d+\)\s*$", "", evidence)
        sc_pat = re.escape(SELF_CHECK_HEAD) + r"\s*(.*?)(?=" + re.escape(ANSWER_HEAD) + r"\s*|$)"
        sc_match = re.search(sc_pat, text, re.DOTALL | re.IGNORECASE)
        if sc_match:
            self_check = sc_match.group(1).strip()
            self_check = re.sub(r"\n+\s*\d+\)\s*$", "", self_check)
        ans_pat = re.escape(ANSWER_HEAD) + r"\s*(\w+)"
        ans_match = re.search(ans_pat, text, re.IGNORECASE)
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

    def process(self, image_path: str | None = None, question: str = "", image_base64: str | None = None) -> Dict[str, Any]:
        """
        入口：拼 prompt → 调 wrapper → 解析三段 → 返回 answer（yes/no/refused）、evidence、self_check、raw。
        图片二选一：image_path 或 image_base64，透传给 wrapper。
        """
        prompt = self._build_prompt(question)
        raw = self.wrapper.predict(image_path=image_path, question=prompt, image_base64=image_base64)
        return self._parse_response(raw)


#======自测======
if __name__ == "__main__":
    import sys
    import os
    _src = os.path.dirname(os.path.abspath(__file__))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    from wrapper import ModelWrapper

    _root = os.path.dirname(_src)
    test_img = os.path.join(_root, "data", "images", "COCO_val2014_000000210789.jpg")
    wrapper = ModelWrapper()
    pipeline = TrustPipeline(wrapper)
    out = pipeline.process(test_img, "Is there a person in the image?")
    print(out)
