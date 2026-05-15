#!/usr/bin/env python3
import os, json, asyncio, unicodedata, secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.environ["BOT_TOKEN"]
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))
JSON_PATH = "libros.json"
PAGINA = 10
DRIVE = "gdrive:Biblioteca Ebooks Español 2026 (epub)/biblioteca/"

def norm(s):
    return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()

print("Cargando libros...", flush=True)
with open(JSON_PATH) as f:
    libros = json.load(f)
print(f"{len(libros)} libros cargados", flush=True)

sesiones = {}
sesiones_libros = {}

def buscar(q, pagina=0, letra='', ext=''):
    q = norm(q.strip()) if q else ''
    res = []
    for l in libros:
        if q:
            t = norm(l['titulo'])
            a = norm(l['autor'])
            if q not in t and q not in a:
                continue
        if letra and (not l['titulo'] or norm(l['titulo'][0]).upper() != letra):
            continue
        if ext and not l['path'].endswith('.' + ext):
            continue
        res.append(l)
    total = len(res)
    res = res[pagina*PAGINA:(pagina+1)*PAGINA]
    return res, total

def fmt_size(b):
    if b > 1e6: return f"{b/1e6:.1f} MB"
    return f"{b/1e3:.0f} KB"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Biblioteca Personal*\n\n"
        "Escribe cualquier texto para buscar libros.\n"
        "Ej: `harry potter` o `gabriel garcia marquez`\n\n"
        "_Case insensitive, sin acentos._",
        parse_mode='Markdown'
    )

async def buscar_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = ' '.join(ctx.args) if ctx.args else ''
    if not q:
        await update.message.reply_text("Escribe el título o autor que quieras buscar")
        return
    res, total = buscar(q)
    if not res:
        await update.message.reply_text("😕 No encontré nada")
        return
    sid = secrets.token_hex(4)
    sesiones[sid] = {'q': q, 'letra': '', 'ext': ''}
    await mostrar_resultados(update.message, res, total, sid, 0)

async def mostrar_resultados(msg, res, total, sid, pagina):
    s = sesiones.get(sid, {})
    texto = f"📖 *{total} resultados*" + (f' para "{s.get("q","")}"' if s.get('q') else '')
    if pagina > 0:
        texto += f" (pág {pagina+1})"
    texto += "\n\n"
    kb = []
    for i, l in enumerate(res):
        tit = l['titulo'][:50]
        btn_text = f"{tit} - {l['autor'][:20]} [{fmt_size(l['size'])}]"
        bid = f"_{sid}_{pagina}_{i}"
        sesiones_libros[bid] = l['path']
        kb.append([InlineKeyboardButton(btn_text, callback_data=bid)])

    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"p:{sid}:{pagina-1}"))
    nav.append(InlineKeyboardButton(f"{pagina+1}/{(total+PAGINA-1)//PAGINA}", callback_data="_"))
    if (pagina+1)*PAGINA < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"p:{sid}:{pagina+1}"))
    kb.append(nav)
    await msg.reply_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("_"):
        path = sesiones_libros.get(data)
        if not path:
            await q.edit_message_text("😕 Sesión expirada, busca de nuevo")
            return
        await q.edit_message_text(f"📥 Descargando...")
        try:
            proc = await asyncio.create_subprocess_exec(
                'rclone', 'cat', DRIVE + path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            data_bytes = await proc.stdout.read()
            await proc.wait()
            if not data_bytes:
                await q.edit_message_text("❌ Error al descargar")
                return
            nombre = path.split('/')[-1]
            await q.message.reply_document(document=data_bytes, filename=nombre)
            await q.edit_message_text(f"✅ Descargado: {nombre}")
        except Exception as e:
            await q.edit_message_text(f"❌ Error: {e}")
        return

    if data.startswith("p:"):
        parts = data.split(':', 2)
        sid = parts[1]
        pagina = int(parts[2])
        s = sesiones.get(sid)
        if not s:
            await q.edit_message_text("😕 Sesión expirada, busca de nuevo")
            return
        res, total = buscar(s['q'], pagina, s['letra'], s['ext'])
        if not res:
            await q.edit_message_text("😕 No hay más resultados")
            return
        await mostrar_resultados(q.message, res, total, sid, pagina)
        return

async def mensaje(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.args = [update.message.text]
    await buscar_cmd(update, ctx)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    app.add_handler(CallbackQueryHandler(callback))

    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/webhook"
        print(f"Iniciando con webhook: {webhook_url}", flush=True)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url,
        )
    else:
        print("Iniciando con polling (sin RENDER_EXTERNAL_URL)", flush=True)
        app.run_polling()

if __name__ == '__main__':
    main()
