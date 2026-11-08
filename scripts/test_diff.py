def diff_texts(old_text, new_text):
    """
    Computes character-level diff between old_text and new_text using LCS.
    Returns (highlighted_new, highlighted_old)
    """
    if not old_text:
        return f'<mark class="diff-add">{new_text}</mark>', ''
    if not new_text:
        return '', f'<del class="diff-del">{old_text}</del>'
    if old_text == new_text:
        return new_text, old_text

    # Dynamic Programming LCS
    m, n = len(old_text), len(new_text)
    # Optimization for long prefixes/suffixes
    prefix_len = 0
    while prefix_len < m and prefix_len < n and old_text[prefix_len] == new_text[prefix_len]:
        prefix_len += 1

    suffix_len = 0
    while suffix_len < (m - prefix_len) and suffix_len < (n - prefix_len) and old_text[m - 1 - suffix_len] == new_text[n - 1 - suffix_len]:
        suffix_len += 1

    common_prefix = old_text[:prefix_len]
    common_suffix = old_text[m - suffix_len:] if suffix_len > 0 else ""

    sub_old = old_text[prefix_len:m - suffix_len] if suffix_len > 0 else old_text[prefix_len:]
    sub_new = new_text[prefix_len:n - suffix_len] if suffix_len > 0 else new_text[prefix_len:]

    # For remaining subparts
    if not sub_old and sub_new:
        return f"{common_prefix}<mark class=\"diff-add\">{sub_new}</mark>{common_suffix}", f"{common_prefix}{common_suffix}"
    if not sub_new and sub_old:
        return f"{common_prefix}{common_suffix}", f"{common_prefix}<del class=\"diff-del\">{sub_old}</del>{common_suffix}"

    return f"{common_prefix}<mark class=\"diff-add\">{sub_new}</mark>{common_suffix}", f"{common_prefix}<del class=\"diff-del\">{sub_old}</del>{common_suffix}"

# Test with APA 128
old_t = "行政處分於法定救濟期間經過後...不得申請。"
new_t = "行政處分於法定救濟期間經過後...不得申請。\n第一項之新證據，指處分作成前已存在或成立而未及調查斟酌，及處分作成後始存在或成立之證據。"

diff_new, diff_old = diff_texts(old_t, new_t)
print("Diff new:")
print(diff_new)
print("Diff old:")
print(diff_old)
