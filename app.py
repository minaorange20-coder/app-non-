import pandas as pd
import re
import random
import requests
import streamlit as st
import io
import os
from urllib.parse import unquote
from deep_translator import GoogleTranslator

# إنشاء مجلد تنزيل الصور تلقائياً
DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# -------------------------------------------------------------
# 1. دوال التوليد والترجمة واستخراج الصور والبيانات
# -------------------------------------------------------------

def generate_egyptian_mobile():
    prefixes = ['010', '011', '012', '015']
    prefix = random.choice(prefixes)
    digits = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return prefix + digits

def generate_egyptian_nid():
    century = random.choice(['2', '3'])
    year = f"{random.randint(50, 99):02d}" if century == '2' else f"{random.randint(0, 24):02d}"
    month = f"{random.randint(1, 12):02d}"
    day = f"{random.randint(1, 28):02d}"
    gov_codes = ['01', '02', '03', '11', '12', '13', '14', '15', '16', '17', '18', '21', '22', '27']
    gov = random.choice(gov_codes)
    sequence = f"{random.randint(1, 9999):04d}"
    checksum = f"{random.randint(1, 9):01d}"
    return f"{century}{year}{month}{day}{gov}{sequence}{checksum}"

def generate_english_owner_name(religion="مسلم"):
    if religion == "مسيحي":
        first_names = ["Mina", "George", "Bishoy", "Fady", "Kirollos", "Mark", "Girgis", "Amir", "Nader", "Wagih"]
        middle_names = ["Gerges", "Ibrahim", "Naguib", "Kamal", "Adly", "Nassef", "Faheem", "Botros"]
        last_names = ["Ibrahim", "Gerges", "Youssef", "Salib", "Habib", "Boulos", "Makram", "Sidhom"]
    else:  # مسلم
        first_names = ["Ahmed", "Mohamed", "Mahmoud", "Mostafa", "Ibrahim", "Ali", "Hassan", "Ayman", "Omar", "Khaled", "Sameh", "Tarek"]
        middle_names = ["Mohamed", "Ahmed", "Ibrahim", "Hassan", "Ali", "Mostafa", "El-Sayed", "Adel", "Mahmoud"]
        last_names = ["Mahmoud", "Ibrahim", "Ali", "Husseini", "Soliman", "Abdelaziz", "Fahmy", "Zaki", "Youssef", "Samy"]
        
    return f"{random.choice(first_names)} {random.choice(middle_names)} {random.choice(last_names)}"

def is_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF]', str(text)))

def translate_text(text, target_lang):
    if not text or str(text).strip() in ["Shop", ""]:
        return str(text)
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(str(text))
        return translated if translated else str(text)
    except Exception:
        return str(text)

def parse_google_maps_url_and_download_photo(url, shop_identifier="shop"):
    coords_x, coords_y = "", ""
    place_name = ""
    downloaded_photo = False
    
    if not url or pd.isna(url):
        return coords_x, coords_y, place_name, downloaded_photo
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
        'Referer': 'https://www.google.com/'
    }
    
    clean_url = str(url).strip()
    
    if "googleusercontent.com" in clean_url or "streetviewpixels-pa" in clean_url:
        try:
            res = requests.get(clean_url, headers=headers, timeout=15)
            if res.status_code == 200 and len(res.content) > 500:
                clean_id = re.sub(r'[^\w\-_\. ]', '_', str(shop_identifier))
                file_name = f"{clean_id}_{random.randint(1000, 9999)}.jpg"
                save_path = os.path.join(DOWNLOADS_DIR, file_name)
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                return "", "", "Shop Image", True
        except Exception:
            pass

    try:
        session = requests.Session()
        response = session.get(clean_url, headers=headers, allow_redirects=True, timeout=12)
        final_url = response.url
        html_content = response.text
    except Exception:
        final_url = clean_url
        html_content = ""

    # استخراج الإحداثيات
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
    if match:
        coords_x = match.group(1)
        coords_y = match.group(2)
    else:
        match_q = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
        if match_q:
            coords_x = match_q.group(1)
            coords_y = match_q.group(2)

    # استخراج اسم المكان من الرابط النهائي
    place_match = re.search(r'/place/([^/@]+)', final_url)
    if place_match:
        raw_name = place_match.group(1)
        place_name = unquote(raw_name).replace('+', ' ').strip()
    else:
        query_match = re.search(r'[?&]q=([^&]+)', final_url)
        if query_match:
            raw_query = query_match.group(1)
            if not re.match(r'^-?\d+\.\d+,-?\d+\.\d+$', raw_query):
                place_name = unquote(raw_query).replace('+', ' ').strip()

    # إذا لم يستخرج الاسم من الرابط، استخرجه من عنوان الصفحة HTML (og:title)
    if not place_name or place_name == "Shop":
        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_content)
        if title_match:
            title_text = title_match.group(1)
            place_name = title_text.split('·')[0].split('-')[0].strip()

    if html_content:
        img_patterns = [
            r'(https://lh[0-9]\.googleusercontent\.com/[^\s"\']+)',
            r'(https://streetviewpixels-pa\.googleapis\.com/v1/thumbnail[^\s"\']+)'
        ]
        
        found_img_url = None
        for pattern in img_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                found_img_url = matches[0]
                break

        if found_img_url:
            try:
                img_res = requests.get(found_img_url, headers=headers, timeout=12)
                if img_res.status_code == 200 and len(img_res.content) > 500:
                    clean_id = re.sub(r'[^\w\-_\. ]', '_', str(shop_identifier))
                    file_name = f"{clean_id}_{random.randint(1000, 9999)}.jpg"
                    save_path = os.path.join(DOWNLOADS_DIR, file_name)
                    with open(save_path, 'wb') as f:
                        f.write(img_res.content)
                    downloaded_photo = True
            except Exception:
                pass

    return coords_x, coords_y, place_name, downloaded_photo

def process_single_row(dial, gmaps_url, shop_en_manual="", shop_ar_manual="", owner_name_manual="", religion="مسلم",
                       channel="Non Telecom-Retail", business_nature="Super_Market", sub_market="Market",
                       region="East Delta and Canal", gov="Kafr El-Sheikh", area="Kafr El-Sheikh", address_manual="",
                       agent_id="105631", field_agent="Mina George Ibrahim", area_manager="Delta vacant",
                       regional="Ibrahim Mohamed El Sherbini", p2p_or_atm="P2P", shop_photo_manual="yes"):
    
    identifier = dial if dial else "Shop"
    cx, cy, auto_name, has_downloaded_img = parse_google_maps_url_and_download_photo(gmaps_url, shop_identifier=identifier) if gmaps_url else ("", "", "", False)
    
    has_manual_en = bool(shop_en_manual and str(shop_en_manual).strip() and not pd.isna(shop_en_manual))
    has_manual_ar = bool(shop_ar_manual and str(shop_ar_manual).strip() and not pd.isna(shop_ar_manual))
    
    if has_manual_en and has_manual_ar:
        final_en_name = str(shop_en_manual).strip()
        final_ar_name = str(shop_ar_manual).strip()
    elif has_manual_ar:
        final_ar_name = str(shop_ar_manual).strip()
        final_en_name = translate_text(final_ar_name, target_lang='en')
    elif has_manual_en:
        final_en_name = str(shop_en_manual).strip()
        final_ar_name = translate_text(final_en_name, target_lang='ar')
    else:
        raw_name = auto_name if auto_name else "Shop"
        if is_arabic(raw_name):
            final_ar_name = raw_name
            final_en_name = translate_text(raw_name, target_lang='en') if raw_name != "Shop" else "Shop"
        else:
            final_en_name = raw_name
            final_ar_name = translate_text(raw_name, target_lang='ar') if raw_name != "Shop" else "Shop"

    if owner_name_manual and str(owner_name_manual).strip() and not pd.isna(owner_name_manual):
        final_owner_name = str(owner_name_manual).strip()
    else:
        final_owner_name = generate_english_owner_name(religion)

    final_shop_photo = "yes" if (has_downloaded_img or shop_photo_manual == "yes") else "no"

    if address_manual and str(address_manual).strip() and not pd.isna(address_manual):
        user_address = str(address_manual).strip()
        if is_arabic(user_address):
            final_ar_address = user_address
            final_en_address = translate_text(user_address, target_lang='en')
        else:
            final_en_address = user_address
            final_ar_address = translate_text(user_address, target_lang='ar')
    elif final_ar_name and final_ar_name != "Shop":
        final_ar_address = f"{gov} - {area} - {final_ar_name}"
        final_en_address = translate_text(final_ar_address, target_lang='en')
    else:
        final_en_address = f"{gov} - {area}"
        final_ar_address = f"{gov}-{area}"

    return {
        'DIAL': str(dial) if not pd.isna(dial) else '',
        'Channel': channel,
        'BUSINESS NATURE ': business_nature,
        'Sub Market': sub_market,
        'Shop NAME ': final_en_name,
        'Shop Arabic Name ': final_ar_name,
        'REGION': region,
        'Gov': gov,
        'Area': area,
        'Address': final_en_address,
        'Arabic Address': final_ar_address,
        'Agent ID': agent_id,
        'Field Agent': field_agent,
        'Area Manager': area_manager,
        'Regional': regional,
        'Owner Name': final_owner_name,
        'Owner Mobile Number': generate_egyptian_mobile(),
        'Owner NID': generate_egyptian_nid(),
        'Wallet Activation Date ': "0",
        'Coordinates X': cx,
        'Coordinates Y': cy,
        'Shop Photo ': final_shop_photo,
        'P2P OR ATM': p2p_or_atm,
        'Date': '',
        'Feedback': ''
    }

# -------------------------------------------------------------
# 2. واجهة التطبيق
# -------------------------------------------------------------

st.set_page_config(page_title="مُولّد شيت المحلات الاحترافي", layout="wide")

st.title("🏪 تطبيق إدخال وتوليد بيانات المحلات (النسخة النهائية للصور)")

tab1, tab2 = st.tabs(["📝 إدخال فردي (Manual Input)", "📁 رفع ملف إكسيل دفعة واحدة (Bulk Processing)"])

if 'data_list' not in st.session_state:
    st.session_state.data_list = []

with tab1:
    with st.form("single_shop_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            dial_input = st.text_input("DIAL (كتابة يدوية)")
            gmaps_url = st.text_input("رابط Google Maps أو رابط الصورة المباشر")
            shop_name_input = st.text_input("اسم المحل بالإنجليزي (اختياري)")
            shop_ar_input = st.text_input("اسم المحل بالعربي (اختياري)")
            address_input = st.text_input("العنوان (اختياري - سيتم استخراجه من اللينك إذا ترك فارغاً)")
            owner_religion = st.selectbox("ديانة صاحب المحل (لتوليد الاسم تلقائياً)", ["مسلم", "مسيحي"])
            owner_name_input = st.text_input("اسم صاحب المحل بالإنجليزي (اختياري)")
            
        with col2:
            channel = st.selectbox("Channel", ["Non Telecom-Retail"], index=0)
            business_nature = st.selectbox("BUSINESS NATURE", ["Super_Market", "Kiosk", "Retail", "Other"])
            sub_market = st.selectbox("Sub Market", ["Market", "Retail"])
            region = st.text_input("REGION", "East Delta and Canal")
            gov = st.text_input("Gov", "Kafr El-Sheikh")
            area = st.text_input("Area", "Kafr El-Sheikh")
            
        with col3:
            agent_id = st.text_input("Agent ID", "105631")
            field_agent = st.text_input("Field Agent", "Mina George Ibrahim")
            area_manager = st.text_input("Area Manager", "Delta vacant")
            regional = st.text_input("Regional", "Ibrahim Mohamed El Sherbini")
            p2p_or_atm = st.selectbox("P2P OR ATM", ["P2P", "ATM"])
            shop_photo = st.selectbox("Shop Photo", ["yes", "no"])

        submitted = st.form_submit_button("➕ إضافة المحل للجدول")

    if submitted:
        row = process_single_row(
            dial=dial_input, gmaps_url=gmaps_url, shop_en_manual=shop_name_input, 
            shop_ar_manual=shop_ar_input, owner_name_manual=owner_name_input, religion=owner_religion,
            channel=channel, business_nature=business_nature, sub_market=sub_market, region=region, 
            gov=gov, area=area, address_manual=address_input, agent_id=agent_id, field_agent=field_agent, 
            area_manager=area_manager, regional=regional, p2p_or_atm=p2p_or_atm, 
            shop_photo_manual=shop_photo
        )
        st.session_state.data_list.append(row)
        st.success(f"تمت الإضافة بنجاح وتنزيل الصورة بشكل سليم! 👈 [المالك: {row['Owner Name']}]")

with tab2:
    st.subheader("📤 رفع شيت يضم الـ DIAL والروابط")
    uploaded_file = st.file_uploader("اختر ملف إكسيل (.xlsx)", type=["xlsx", "xls"])
    bulk_religion = st.selectbox("اختر الديانة العامة للملف المرفوع:", ["مسلم", "مسيحي"], key="bulk_rel")
    
    if uploaded_file is not None:
        try:
            input_df = pd.read_excel(uploaded_file)
            st.write("📊 معاينة أولية للملف المرفوع:")
            st.dataframe(input_df.head(5))
            
            all_cols = input_df.columns.tolist()
            options = ["-- غير محدد --"] + all_cols
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                dial_col = st.selectbox("حدد عمود الـ DIAL (مطلوب):", all_cols, index=0 if 'DIAL' not in all_cols else all_cols.index('DIAL'))
                url_col = st.selectbox("حدد عمود الرابط (مطلوب):", all_cols, index=0 if 'URL' not in all_cols else all_cols.index('URL'))
            
            with col_sel
