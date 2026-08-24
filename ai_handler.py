import google.genai as genai
import requests
from bs4 import BeautifulSoup
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

def search_topic(topic: str) -> str:
    """Google qidiruvdan mavzu bo'yicha ma'lumot olish"""
    try:
        search_url = f"https://www.google.com/search?q={topic}+uz"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')

        texts = []
        for div in soup.find_all('div', class_='VwiC3b')[:3]:
            text = div.get_text()
            if text:
                texts.append(text)

        return " ".join(texts) if texts else f"{topic} haqida umumiy ma'lumot"
    except Exception as e:
        return f"{topic} haqida ma'lumot topib bo'lmadi: {str(e)}"

def generate_post(topic: str, source_text: str = None) -> str:
    """AI bilan qiziqarli post yaratish"""
    if not source_text:
        source_text = search_topic(topic)

    prompt = f"""
    Siz qisqa va tushunarli post yozasiz.
    Mavzu: {topic}
    Manba: {source_text}

    Ko'rsatmalar:
    1. Post 80-120 so'z bo'lsin (qisqa va aniq)
    2. 2-3 ta emoji qo'sh (ortiqcha bo'lmasin)
    3. Oxirida asos: [📌 Asos: {topic}] ko'rinishida yoz
    4. * yulduzcha belgi ishlatma
    5. O'zbek tilida oddiy yoz
    6. Hamma uchun tushunarli bo'lsin

    Faqat postni yoz, boshqa qo'shma.
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text

def refine_post(original_post: str, feedback: str = "") -> str:
    """Postni qayta ishlash va takomillash"""
    prompt = f"""
    Quyidagi postni takomillash:

    Asl post:
    {original_post}

    Foydalanuvchi taklifi: {feedback if feedback else "Qisqartir va soddalashtr"}

    Ko'rsatmalar:
    1. Postni 80-120 so'zga qisqartir
    2. Foydalanuvchi taklifi bo'yicha o'zgar
    3. 2-3 ta emoji qo'sh (ortiqcha bo'lmasin)
    4. * yulduzcha belgi ishlatma
    5. Oxirida asos: [📌 Asos] ko'rinishida qo'sh
    6. O'zbek tilini sodda qol

    Faqat yangi postni yoz, boshqa qo'shma.
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text

