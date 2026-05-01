import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from google import genai

# Create Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


@csrf_exempt
def ai_coach_response(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            prompt = data.get("prompt", "").strip()

            if not prompt:
                return JsonResponse({"response": "Please enter a question."})

            # 🔥 Normalize prompt for better matching
            lower_prompt = prompt.lower()

            # 🔥 Smart context for recommendations
            extra_context = ""

            if any(word in lower_prompt for word in ["python", "java", "coding", "programming", "dsa"]):
                extra_context = "Focus more on Programming section for hands-on coding practice."

            elif any(word in lower_prompt for word in ["aptitude", "reasoning", "logical", "math"]):
                extra_context = "Focus more on Aptitude section for problem-solving practice."

            elif any(word in lower_prompt for word in ["hr", "communication", "tell me about yourself", "behavioral"]):
                extra_context = "Focus more on Communication section for HR interview preparation."

            elif any(word in lower_prompt for word in ["company", "interview experience", "glassdoor"]):
                extra_context = "Focus more on Company Insights section."

            else:
                extra_context = "Also guide the user to explore AI Dashboard for personalized preparation."

            # 🔥 Final prompt to Gemini
            final_prompt = f"""
You are a friendly AI interview coach inside a platform called PrepEdge.

Your job:
1. Give a simple, clear answer
2. Suggest relevant learning sections available inside PrepEdge

PrepEdge has these sections:
- Programming (coding practice)
- Aptitude (MCQs & reasoning)
- Communication (HR & soft skills)
- Company Insights (interview experiences)
- AI Dashboard (personalized learning)

Guidance:
{extra_context}

Rules:
- Use SIMPLE English (like ChatGPT)
- Keep sentences short
- No complex words
- No corporate tone
- Be practical and helpful

Format:
1. Give answer in 4–5 bullet points
2. Add one small example if useful
3. Then add:

👉 Recommended on PrepEdge:
• Suggest 2–3 relevant sections from above list

Keep everything clean and easy to read.

Question: {prompt}
"""

            # ✅ Gemini API call
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=final_prompt
            )

            ai_text = response.text.strip() if response.text else "Try asking in a different way."

            return JsonResponse({"response": ai_text})

        except Exception as e:
            print("❌ Gemini Error:", e)
            return JsonResponse({
                "response": "⚠️ AI service error. Please try again later."
            })

    return JsonResponse({"response": "Invalid request method."})