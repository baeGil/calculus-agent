import json
import re

# The string exactly as the user reported (simulating LLM output)
# Note: In Python string literal, I need to represent what the LLM likely outputted.
# If LLM outputted: "content": "\frac..."
# That is invalid JSON. It should be "\\frac..."

llm_output = r"""
{
  "questions": [
    {
      "id": 1,
      "content": "Tính tích phân $\iint\limits_{D} \frac{x^2 + 2}{x^2 + y^2 + 4} \, dxdy$, với $D$ là miền giới hạn bởi hình vuông $|x| + |y| = 1$.",
      "type": "code",
      "tool_input": "Viết code Python để tính tích phân kép của hàm f(x,y) = (x^2 + 2)/(x^2 + y^2 + 4) trên miền D là hình vuông |x| + |y| = 1"
    },
    {
      "id": 2,
      "content": "Tính tích phân $\iint\limits_{D} \frac{y^2 + 8}{x^2 + y^2 + 16} \, dxdy$, với $D$ là miền giới hạn bởi hình vuông $|x| + |y| = 2$.",
      "type": "code",
      "tool_input": "Viết code Python để tính tích phân kép của hàm f(x,y) = (y^2 + 8)/(x^2 + y^2 + 16) trên miền D là hình vuông |x| + |y| = 2"
    }
  ]
}
"""

print("--- Testing Raw JSON Load ---")
try:
    data = json.loads(llm_output)
    print("✅ JSON Load Success")
except json.JSONDecodeError as e:
    print(f"❌ JSON Load Failed: {e}")

print("\n--- Testing Regex Fix Strategy ---")
# Strategy: Look for backslashes that are NOT followed by specific JSON control chars
# But in JSON, only \", \\, \/, \b, \f, \n, \r, \t, \uXXXX contain backslashes.
# LaTeX backslashes like \f in \frac are form feeds? No, \f is form feed.
# \i in \iint is invalid.


def fix_json_latex(text):
    """
    Repair JSON string containing unescaped LaTeX backslashes.
    Example: "\frac" -> "\\frac"
    """
    # Pattern: Match a backslash that is NOT followed by valid JSON escape chars
    # Valid escapes: " \ / b f n r t u
    # Note: \u needs 4 hex digits.
    
    # Negative lookahead is useful here.
    # We want to match \ where next char is NOT one of " \ / b f n r t u
    
    # But wait, \f is Form Feed in JSON. In LaTeX it is \frac.
    # If LLM outputs "\frac", Python sees `\f` (form feed) + `rac`?
    # No, we get the raw string from LLM.
    # LLM outputting literal "\frac" means backslash + f + r + a + c.
    # In JSON string "\frac", the parser sees `\f` (escape for form feed) + `rac`. Valid syntax? Yes.
    # But "\iint": `\i` is Invalid escape.
    
    # So the problem is mainly mostly invalid escapes like \i, \l, \s, \x, etc.
    # AND valid escapes that are actually LaTeX (like \t -> tab, but meant \text).
    
    # HEURISTIC: Double ALL backslashes, then un-double the valid JSON control ones?
    # No, that's messy.
    
    # Better: Match `\` that is followed by something looking like a LaTeX command (alpha chars).
    # But technically `\n` is Newline.
    
    # Robust Strategy used in other projects:
    # 1. Replace `\\` with `ROOT_BACKSLASH_PLACEHOLDER`
    # 2. Replace `\` with `\\` IF it's not a valid escape?
    
    # Let's try simple regex: escape ALL backslashes first?
    # LLM usually sends plain text.
    # If we do `text.replace("\\", "\\\\")`, then `\n` becomes `\\n` (literal \n).
    # `json.loads` will read it as literally backslash+n.
    # This might be SAFER for content fields!
    
    # But we have structure: `{"questions": ...}`. We don't want to break `\"` for quotes.
    
    # Correct Regex: Match `\` that is NOT followed by `"` (quote).
    # Because we assume structure uses quotes.
    # But what about `\n` inside the content? 
    # If LLM meant newline, it sends `\n`. If we escape it to `\\n`, we get literal \n.
    # If LLM meant LaTeX `\frac`, it sends `\f...`. If we escape to `\\f...`, we get literal \f... (which is what we want for LaTeX source).
    
    # So escaping `\` -> `\\` is generally safe EXCEPT for:
    # 1. `\"` (which closes the string) -> We MUST keep `\"` as `\"` (escaped quote).
    # 2. `\\` (literal backslash) -> We probably want to keep it or double it?
    
    # Proposal:
    # Replace `\` with `\\` UNLESS it is followed by `"`
    
    new_text = re.sub(r'\\(?!"|u[0-9a-fA-F]{4})', r'\\\\', text)
    # Exclude unicode \uXXXX too
    
    # Also need to NOT double existing double backslashes?
    # Text: `\\frac` -> regex sees backslash, not followed by quote -> `\\\\frac`.
    # `json.loads` sees `\\` -> literal backslash. `frac` -> literal frac. Result: `\frac`. Correct.
    # Text: `\frac` -> regex sees backslash -> `\\frac`.
    # `json.loads` sees `\` (invalid?) -> No, `\\` becomes `\`. `frac`. Result: `\frac`.
    
    # Wait, `json.loads("\\frac")` -> in python string `\\frac`. Parser see `\` then `f`. `\f` is valid escape?
    # No, `\\` in JSON string means "Literal Backslash".
    # So `{"a": "\\frac"}` -> python dict `{'a': '\\frac'}`.
    
    # The Regex `r'\\(?!"|u[0-9a-fA-F]{4})'` matches any backslash NOT followed by quote or unicode.
    # Replacement: `\\\\` (double backslash string, usually means 2 chars `\` `\`).
    
    return new_text

print(f"Original len: {len(llm_output)}")
fixed = fix_json_latex(llm_output)
print(f"Fixed start: {fixed[:100]}...")

try:
    data = json.loads(fixed)
    print("✅ Repair Success!")
    print(f"Question 1 Content: {data['questions'][0]['content'][:50]}...")
except json.JSONDecodeError as e:
    print(f"❌ Repair Failed: {e}")

