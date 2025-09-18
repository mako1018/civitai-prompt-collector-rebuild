def clean_prompts(raw_items):
    """
    必要なフィールドだけ残す & 重複を削除
    """
    prompts = []
    seen_ids = set()

    for item in raw_items:
        prompt_id = item.get("id")
        prompt_text = item.get("prompt")

        if not prompt_id or not prompt_text:
            continue
        if prompt_id in seen_ids:
            continue

        seen_ids.add(prompt_id)
        prompts.append({
            "id": prompt_id,
            "text": prompt_text
        })

    return prompts

