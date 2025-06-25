from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import BadRequest
import datetime
import os
import subprocess
import whisper
import asyncio
import csv
from transformers import pipeline
from gtts import gTTS
import random
import nest_asyncio
from faster_whisper import WhisperModel
whisper_model = WhisperModel("base", compute_type="int8")
TOKEN = '7938652871:AAHqUgFL6FSHSCEmhq9TU69HYerXII2vm2o'

user_last_choice = {}
subscribed_users = {}  
user_consent = {}  # {user_id: True/False}

sentiment_analyzer = pipeline("sentiment-analysis", model="MilaNLProc/feel-it-italian-sentiment")
whisper_model = whisper.load_model("base")

# === TASTIERA PRINCIPALE ===
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ Testo", callback_data='testo'),
            InlineKeyboardButton("🎙️ Voce", callback_data='voce'),
            InlineKeyboardButton("📹 Video", callback_data='video')
        ],
        [
            InlineKeyboardButton("🎯 Enfasi", callback_data='enfasi'),
            InlineKeyboardButton("🎵 Intonazione", callback_data='intonazione'),
            InlineKeyboardButton("📏 Chiarezza", callback_data='chiarezza'),
        ],
        [
            InlineKeyboardButton("🎲 Sfida random", callback_data='sfida_random')
        ],
        [
            InlineKeyboardButton("🔄 Inizia di nuovo", callback_data='restart'),
            InlineKeyboardButton("📩 Imposta orario motivazionale", callback_data='set_orario')
        ]
    ])

# === CONSENSO PRIVACY ===
async def handle_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    traccia_uso(user_id, "consenso", query.data)
    if query.data == "consent_si":
        user_consent[user_id] = True
        await query.edit_message_text("✅ Grazie per il consenso! Ora puoi iniziare.")
        await show_menu(query.message)
    else:
        user_consent[user_id] = False
        await query.edit_message_text("🔒 Hai scelto di non proseguire. I tuoi dati non saranno salvati.")

async def show_menu(message):
    await message.reply_text(
        "👋 Ciao! Sono Nèa, il tuo coach personale. Scegli su cosa vuoi lavorare oggi:",
        reply_markup=get_main_keyboard()
    )

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_consent.get(user_id):
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Acconsento", callback_data="consent_si"),
                InlineKeyboardButton("❌ No, grazie", callback_data="consent_no")
            ]
        ])
        await update.message.reply_text(
            "🛡️ *Privacy e Consenso*\nPer offrirti feedback, elaboriamo vocali e video localmente.\n\nVuoi procedere?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return
    if update.message:
        await show_menu(update.message)
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "👋 Ciao! Sono Nèa, il tuo coach personale. Scegli su cosa vuoi lavorare oggi:",
            reply_markup=get_main_keyboard()
        )

# === HANDLE CHOICE ===
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Rispondi SUBITO alla callback query

    user_id = query.from_user.id
    choice = query.data
    traccia_uso(user_id, "scelta_menu", choice)
    sfida_extra = get_random_challenge()
    user_last_choice[query.from_user.id] = choice
    if choice == 'enfasi':
        text = (
            "💬 *Stai parlando con Nèa...*\n\n"
            "🎯 *Allenamento di oggi: Enfasi*\n\n"
            "🔥 *Missione:* Dai forza alle parole importanti.\n"
            "🗣️ *Frase guida:* _“Questa idea potrebbe cambiare tutto.”_\n\n"
            "💥 Fai sentire l'impatto delle tue parole. Quando sei pronto, inviami un vocale!\n\n"
           f"✨ Vuoi una sfida extra per allenarti?\n\n{sfida_extra}"
        )
    elif choice == 'intonazione':
        text = (
            "💬 *Stai parlando con Nèa...*\n\n"
            "🎵 *Allenamento di oggi: Intonazione*\n\n"
            "🎯 *Missione:* Dai ritmo e vita a ciò che dici.\n"
            "🗣️ *Frase guida:* _“Mi sento pronto e motivato.”_\n\n"
            "📣 Immagina di ispirare chi ti ascolta. Quando sei pronto, inviami un vocale!\n\n"
            f"✨ Vuoi una sfida extra per allenarti?\n\n{sfida_extra}"
        )
    elif choice == 'chiarezza':
        text = (
            "💬 *Stai parlando con Nèa...*\n\n"
            "📏 *Allenamento di oggi: Chiarezza*\n\n"
            "🎯 *Missione:* Comunica con semplicità e precisione.\n"
            "🗣️ *Frase guida:* _“Ti spiego tutto in modo chiaro e semplice.”_\n\n"
            "🧠 Sii diretto e ordinato. Quando sei pronto, inviami un vocale!\n\n"
            f"✨ Vuoi una sfida extra per allenarti?\n\n{sfida_extra}"
        )
    elif choice == 'testo':
        text = "✍️ Scrivi un messaggio e ti darò un feedback sul tono e la chiarezza!"
    elif choice == 'voce':
        text = "🎤 Inviami un vocale per ricevere feedback!"
    elif choice == 'video':
        text = "📹 Inviami un video e ti risponderò entro 4 ore con un’analisi posturale."
    elif choice == 'sfida_random':
        random_challenge = get_random_challenge()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎲 Ecco la tua nuova sfida casuale:\n\n{random_challenge}"
        )
        return
    elif choice == 'restart':
        await start(update, context)
        return
    elif choice == 'subscribe':
        subscribed_users[query.from_user.id] = "09:00"
        text = "🎉 Ti invierò un messaggio motivazionale ogni giorno alle 9:00!"
    else:
        return

    try:
        await query.edit_message_text(
            text=f"{text}\n\nScegli un'altra opzione se vuoi:",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

# === MOTIVAZIONALE ===
def frase_motivazionale_random(path="frasi_motivazionali.txt"):
    with open(path, encoding="utf-8") as f:
        frasi = [r.strip() for r in f if r.strip()]
    return random.choice(frasi)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import random

def get_random_challenge():
    challenges = [
        {
            "title": "🎯 Allenamento: Intonazione",
            "mission": "Modula il tono per dare emozione.",
            "phrase": "Non ci crederai mai, ma è successo davvero!"
        },
        {
            "title": "🎯 Allenamento: Chiarezza",
            "mission": "Parla lentamente e scandisci bene.",
            "phrase": "Questa è la soluzione più semplice ed efficace."
        },
        {
            "title": "🎯 Allenamento: Pausa",
            "mission": "Usa le pause per creare attenzione.",
            "phrase": "Aspetta... questa parte è fondamentale."
        },
        {
            "title": "🎯 Allenamento: Coinvolgimento",
            "mission": "Fai sentire chi ascolta parte della storia.",
            "phrase": "Immagina di essere proprio lì, al mio fianco."
        },
        {
            "title": "🎯 Allenamento: Ritmo",
            "mission": "Alterna velocità per dare energia.",
            "phrase": "Prima tutto era calmo... poi è cambiato tutto."
        }
    ]

    selected = random.choice(challenges)
    return (
        f"{selected['title']}\n"
        f"🔥 Missione: {selected['mission']}\n"
        f"🗣️ Frase guida: “{selected['phrase']}”\n\n"
        "🎤 Quando sei pronto, inviami un vocale!"
    )

async def scheduler_messaggi(app):
    while True:
        now = datetime.datetime.now()
        ora_corrente = now.strftime("%H:%M")
        for user_id, orario in subscribed_users.items():
            if ora_corrente == orario:
                frase = frase_motivazionale_random()
                try:
                    await app.bot.send_message(chat_id=user_id, text=f"🌟 *Frase del giorno:* {frase}", parse_mode="Markdown")
                except: pass
        await asyncio.sleep(60)

async def chiedi_orario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⏰ 07:00", callback_data="ora_07:00"),
         InlineKeyboardButton("☕️ 09:00", callback_data="ora_09:00")],
        [InlineKeyboardButton("🌞 12:00", callback_data="ora_12:00"),
         InlineKeyboardButton("🌇 18:00", callback_data="ora_18:00")]
    ]
    await update.message.reply_text("⏰ A che ora vuoi ricevere il messaggio ogni giorno?", reply_markup=InlineKeyboardMarkup(keyboard))

async def salva_orario_scelto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    orario = query.data.replace("ora_", "")
    subscribed_users[user_id] = orario
    traccia_uso(user_id, "imposta_orario", orario)
    await query.edit_message_text(f"✅ Ti invierò il messaggio ogni giorno alle {orario}!")
    frase = frase_motivazionale_random()
    await context.bot.send_message(chat_id=user_id, text=f"🌟 *Frase del giorno:* {frase}", parse_mode="Markdown")

# === UTILITÀ ===
def punteggio_motivazione(testo):
    result = sentiment_analyzer(testo)[0]
    label, score = result['label'], result['score']
    # Base energia su sentiment
    if label in ["LABEL_2", "positive"]:
        energia = round(8.0 + score * 2, 1)  # 8-10
        coinvolgimento = "Ottimo"
    elif label in ["LABEL_1", "neutral"]:
        energia = round(5.0 + score * 2, 1)  # 5-7
        coinvolgimento = "Buono"
    else:
        energia = round(3.0 + score * 2, 1)  # 3-5
        coinvolgimento = "Basso"
    return energia, coinvolgimento

def genera_audio_risposta(testo, filename):
    gTTS(text=testo, lang='it').save(filename)

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_consent.get(user_id):
        # Mostra richiesta consenso solo la prima volta
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Acconsento", callback_data="consent_si"),
                InlineKeyboardButton("❌ No, grazie", callback_data="consent_no")
            ]
        ])
        await update.message.reply_text(
            "🛡️ *Privacy e Consenso*\nPer offrirti feedback, elaboriamo vocali e video localmente.\n\nVuoi procedere?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return
    # Se già acconsentito, mostra il menu
    keyboard = [
        [
            InlineKeyboardButton("✍️ Testo", callback_data='testo'),
            InlineKeyboardButton("🎙️ Voce", callback_data='voce'),
            InlineKeyboardButton("📹 Video", callback_data='video')
        ],
        [
            InlineKeyboardButton("🎯 Enfasi", callback_data='enfasi'),
            InlineKeyboardButton("🎵 Intonazione", callback_data='intonazione'),
            InlineKeyboardButton("📏 Chiarezza", callback_data='chiarezza'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Se è un comando /start da messaggio
    if update.message:
        await update.message.reply_text(
            "👋 Ciao! Sono Nèa, il tuo coach personale. Scegli su cosa vuoi lavorare oggi:",
            reply_markup=reply_markup
        )
    # Se viene da pulsante (callback query)
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "👋 Ciao! Sono Nèa, il tuo coach personale. Scegli su cosa vuoi lavorare oggi:",
            reply_markup=reply_markup
        )
# === TESTO ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_consent.get(user_id):
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Acconsento", callback_data="consent_si"),
                InlineKeyboardButton("❌ No, grazie", callback_data="consent_no")
            ]
        ])
        await update.message.reply_text(
            "Devi prima accettare la privacy per usare questa funzione.\nVuoi procedere?",
            reply_markup=keyboard
        )
        return

    testo = update.message.text
    result = sentiment_analyzer(testo)[0]
    label, score = result['label'], result['score']
    # Etichette più chiare
    if label in ["LABEL_2", "positive"]:
        giudizio = "😊 Il tono è positivo!"
        consiglio = "Continua così! La tua energia si sente forte e chiara."
        sfida = ""
    elif label in ["LABEL_1", "neutral"]:
        giudizio = "😐 Tono neutro."
        consiglio = "Prova a coinvolgere un po' di più chi ti ascolta, ad esempio aggiungendo emozione o esempi."
        sfida = ""
    else:
        giudizio = "😟 Tono negativo."
        consiglio = "Cerca di esprimere il tuo punto di vista con un linguaggio più propositivo."
        sfida = f"\n\n💪 *Sfida del giorno*: {frase_motivazionale_random()}"

    feedback = f"🧠 *Analisi:* {label} ({score:.2f})\n{giudizio}\n💡 *Consiglio:* {consiglio}{sfida}"
    await update.message.reply_text(feedback, parse_mode="Markdown", reply_markup=get_main_keyboard())

    with open("analisi_testi.csv", "a", encoding="utf-8", newline='') as f:
        csv.writer(f).writerow([datetime.datetime.now(), update.effective_user.id, testo, label, score])

    traccia_uso(user_id, "testo", update.message.text)

# === VOCE ===
def salva_csv_voce(testo, user_id, scelta, ogg_path, wav_path):
    with open("trascrizioni_vocali.csv", "a", newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            datetime.datetime.now().isoformat(), user_id, testo, "voce", scelta, ogg_path, wav_path
        ])

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_consent.get(user_id):
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Acconsento", callback_data="consent_si"),
                InlineKeyboardButton("❌ No, grazie", callback_data="consent_no")
            ]
        ])
        await update.message.reply_text(
            "Devi prima accettare la privacy per usare questa funzione.\nVuoi procedere?",
            reply_markup=keyboard
        )
        return

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    folder = "vocali"
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    ogg_path, wav_path = f"{folder}/v_{timestamp}.ogg", f"{folder}/v_{timestamp}.wav"

    await file.download_to_drive(ogg_path)
    subprocess.run(["ffmpeg", "-i", ogg_path, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    segments, info = whisper_model.transcribe(wav_path, language="it")
    testo = " ".join([seg.text for seg in segments])

    if not testo:
        await update.message.reply_text("⚠️ Nessun contenuto rilevato.")
        return

    energia, coinvolgimento = punteggio_motivazione(testo)
    audio_path = f"{folder}/f_{timestamp}.mp3"
    genera_audio_risposta(f"Hai parlato con energia {energia} su 10. Continua così!", audio_path)

    await update.message.reply_text(f"📝 Trascrizione:\n_{testo}_", parse_mode="Markdown", reply_markup=get_main_keyboard())
    await update.message.reply_text(f"🔥 Energia: {energia}/10 🎯 Coinvolgimento: {coinvolgimento}")
    with open(audio_path, 'rb') as audio:
        await update.message.reply_voice(voice=audio, caption="🎧 Feedback vocale")

    scelta = user_last_choice.get(update.effective_user.id, "non specificata")
    salva_csv_voce(testo, update.effective_user.id, scelta, ogg_path, wav_path)

    traccia_uso(user_id, "voce", testo)

# === VIDEO ===
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_consent.get(user_id):
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Acconsento", callback_data="consent_si"),
                InlineKeyboardButton("❌ No, grazie", callback_data="consent_no")
            ]
        ])
        await update.message.reply_text(
            "Devi prima accettare la privacy per usare questa funzione.\nVuoi procedere?",
            reply_markup=keyboard
        )
        return

    video = update.message.video
    file = await context.bot.get_file(video.file_id)
    folder = "video"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    await file.download_to_drive(path)
    await update.message.reply_text("📹 Video ricevuto. Analisi pronta entro 4 ore.", reply_markup=get_main_keyboard())

    traccia_uso(user_id, "video")
def utenti_attivi():
    """Restituisce il numero di utenti che hanno dato il consenso privacy."""
    return sum(1 for v in user_consent.values() if v)


def traccia_uso(user_id, tipo, dettaglio=""):
    with open("log_utilizzo.csv", "a", encoding="utf-8", newline='') as f:
        csv.writer(f).writerow([
            datetime.datetime.now().isoformat(), user_id, tipo, dettaglio
        ])

async def utenti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = utenti_attivi()
    await update.message.reply_text(f"👥 Utenti attivi (che hanno dato il consenso): {n}")
# === AVVIO ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Comandi
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orario", chiedi_orario))
    app.add_handler(CommandHandler("utenti", utenti))

    # Callback (pulsanti)
    app.add_handler(CallbackQueryHandler(handle_consent, pattern="^consent_"))
    app.add_handler(CallbackQueryHandler(salva_orario_scelto, pattern="^ora_"))
    app.add_handler(CallbackQueryHandler(handle_choice))

    # Messaggi
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    # Avvio scheduler e bot
    asyncio.create_task(scheduler_messaggi(app))
    print("🤖 Nèa attiva.")
    await app.run_polling()

nest_asyncio.apply()
asyncio.run(main())

