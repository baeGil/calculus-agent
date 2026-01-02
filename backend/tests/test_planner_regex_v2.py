import json
import re

# Exact text from User (Step 3333). 
# I am using a raw string r'' to represent what likely came out of the LLM before any python processing.
# BUT, if the user copy-pasted from a log that already had escapes...
# Let's assume the LLM output raw LaTeX single backslashes.

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

print(f"Original Length: {len(llm_output)}")

# Current Logic in nodes.py
def current_repair(text):
    return re.sub(r'\\(?!"|u[0-9a-fA-F]{4})', r'\\\\', text)

print("\n--- Testing Current Repair Logic ---")
fixed = current_repair(llm_output)
print(f"Fixed snippet: {fixed[50:150]}...")

try:
    data = json.loads(fixed)
    print("✅ JSON Load Success")
    print(data['questions'][0]['content'])
except json.JSONDecodeError as e:
    print(f"❌ JSON Load Failed: {e}")
    # Inspect around error
    print(f"Error Context: {fixed[e.pos-10:e.pos+10]}")

print("\n--- Testing Improved Logic (Lookbehind?) ---")
# If the current logic fails, we need to know why.
# Maybe it double-escapes existing double-escapes?
# If input is `\\iint` (valid), regex sees `\` (first one) not followed by quote. Replaces with `\\\\`.
# Result `\\\\` + `iint`? No, `\\\\` + `\iint` (second slash remains)?
# Let's see what happens.
