# -*- coding: utf-8 -*-
__version__ = "1.0.0"

import sqlite3
from datetime import datetime, date
from pathlib import Path

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

DB_PATH = Path(__file__).with_name("expenses.db")

KV = r"""
#:import dp kivy.metrics.dp
BoxLayout:
    orientation: "vertical"
    padding: dp(14)
    spacing: dp(10)

    canvas.before:
        Color:
            rgba: (0.95, 0.96, 0.98, 1)
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: "مدیریت هزینه‌ها"
        font_size: "24sp"
        bold: True
        color: (0.08, 0.16, 0.25, 1)
        size_hint_y: None
        height: dp(48)

    BoxLayout:
        size_hint_y: None
        height: dp(80)
        padding: dp(12)
        canvas.before:
            Color:
                rgba: (0.10, 0.42, 0.34, 1)
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(14)]
        orientation: "vertical"
        Label:
            text: "مجموع هزینه‌های امروز"
            color: (1, 1, 1, 1)
            font_size: "15sp"
        Label:
            id: today_total
            text: "۰ تومان"
            color: (1, 1, 1, 1)
            bold: True
            font_size: "22sp"

    TextInput:
        id: item
        hint_text: "چی خریدی؟ مثلاً ناهار، بنزین، خرید مغازه"
        multiline: False
        size_hint_y: None
        height: dp(48)
        font_size: "16sp"

    TextInput:
        id: amount
        hint_text: "مبلغ به تومان (مثلاً 250000)"
        multiline: False
        input_filter: "int"
        size_hint_y: None
        height: dp(48)
        font_size: "16sp"

    Spinner:
        id: account
        text: "انتخاب حساب پرداخت‌کننده"
        values: ("پول نقد", "بانک ملی", "بانک ملت", "بانک صادرات", "بانک سامان", "حساب مغازه", "سایر")
        size_hint_y: None
        height: dp(48)
        font_size: "16sp"

    TextInput:
        id: note
        hint_text: "توضیح اضافی (اختیاری)"
        multiline: False
        size_hint_y: None
        height: dp(48)
        font_size: "16sp"

    Button:
        text: "ثبت خرید"
        size_hint_y: None
        height: dp(52)
        background_normal: ""
        background_color: (0.10, 0.42, 0.34, 1)
        font_size: "18sp"
        on_release: app.add_expense()

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        Button:
            text: "گزارش امروز"
            on_release: app.show_daily_report()
        Button:
            text: "آخرین خریدها"
            on_release: app.show_recent()

    Label:
        text: "اطلاعات روی همین گوشی ذخیره می‌شود."
        color: (0.35, 0.38, 0.42, 1)
        font_size: "12sp"
        size_hint_y: None
        height: dp(24)
"""

def format_money(value):
    return f"{value:,} تومان"

class ExpenseManagerApp(App):
    title = "مدیریت هزینه‌ها"

    def build(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                amount INTEGER NOT NULL,
                account TEXT NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()
        root = Builder.load_string(KV)
        self.refresh_total(root)
        return root

    def refresh_total(self, root=None):
        root = root or self.root
        today = date.today().isoformat()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE substr(created_at,1,10)=?",
            (today,)
        ).fetchone()
        root.ids.today_total.text = format_money(row[0])

    def message(self, title, message):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        box.add_widget(Label(text=message, halign="right", valign="middle"))
        close = __import__("kivy.uix.button", fromlist=["Button"]).Button(
            text="باشه", size_hint_y=None, height=dp(44)
        )
        box.add_widget(close)
        popup = Popup(title=title, content=box, size_hint=(0.88, 0.65))
        close.bind(on_release=popup.dismiss)
        popup.open()

    def add_expense(self):
        item = self.root.ids.item.text.strip()
        amount_text = self.root.ids.amount.text.strip()
        account = self.root.ids.account.text
        note = self.root.ids.note.text.strip()

        if not item:
            self.message("اطلاعات ناقص", "لطفاً نام خرید را وارد کن.")
            return
        if not amount_text or not amount_text.isdigit() or int(amount_text) <= 0:
            self.message("مبلغ نامعتبر", "مبلغ را به تومان و فقط با عدد وارد کن.")
            return
        if account == "انتخاب حساب پرداخت‌کننده":
            self.message("حساب انتخاب نشده", "لطفاً حساب پرداخت‌کننده را انتخاب کن.")
            return

        amount = int(amount_text)
        self.conn.execute(
            "INSERT INTO expenses (item, amount, account, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (item, amount, account, note, datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()
        self.root.ids.item.text = ""
        self.root.ids.amount.text = ""
        self.root.ids.note.text = ""
        self.root.ids.account.text = "انتخاب حساب پرداخت‌کننده"
        self.refresh_total()
        self.message("ثبت شد", f"«{item}» به مبلغ {format_money(amount)} ثبت شد.")

    def show_daily_report(self):
        today = date.today().isoformat()
        rows = self.conn.execute("""
            SELECT item, amount, account, created_at
            FROM expenses WHERE substr(created_at,1,10)=?
            ORDER BY created_at DESC
        """, (today,)).fetchall()
        total = sum(row[1] for row in rows)
        lines = [f"جمع امروز: {format_money(total)}", f"تعداد خریدها: {len(rows)}", ""]
        if rows:
            for item, amount, account, created_at in rows:
                t = datetime.fromisoformat(created_at).strftime("%H:%M")
                lines.append(f"{t} | {item} | {format_money(amount)} | {account}")
        else:
            lines.append("امروز خریدی ثبت نشده است.")
        by_account = self.conn.execute("""
            SELECT account, SUM(amount) FROM expenses
            WHERE substr(created_at,1,10)=? GROUP BY account ORDER BY SUM(amount) DESC
        """, (today,)).fetchall()
        if by_account:
            lines += ["", "تفکیک حساب‌ها:"]
            lines += [f"{account}: {format_money(amount)}" for account, amount in by_account]
        self.message("گزارش امروز", "\n".join(lines))

    def show_recent(self):
        rows = self.conn.execute("""
            SELECT item, amount, account, created_at FROM expenses
            ORDER BY id DESC LIMIT 20
        """).fetchall()
        lines = []
        for item, amount, account, created_at in rows:
            dt = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
            lines.append(f"{dt}\n{item} — {format_money(amount)}\nحساب: {account}")
        self.message("آخرین خریدها", "\n\n".join(lines) if lines else "هنوز خریدی ثبت نشده.")

    def on_stop(self):
        if hasattr(self, "conn"):
            self.conn.close()

if __name__ == "__main__":
    ExpenseManagerApp().run()
