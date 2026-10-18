"""TOPDIM mobil ilovasi (Android).

Flet kutubxonasi yordamida Python'da yozilgan: Flet ilova oynasini Flutter
orqali chizadi, mantiq esa oddiy Python kodi. APK yig'ish:

    cd mobile
    flet build apk

Ilova o'zi ma'lumot saqlamaydi — hammasi TOPDIM serverida (bot bilan bitta
baza). Server manzili va kirish tokeni telefonda SharedPreferences'da turadi.

Ekranlar (pastki menyu):
    E'lonlar      — qidiruv va kategoriya bo'yicha faol e'lonlar
    E'lon berish  — yangi e'lon (Telegram orqali kirish kerak)
    Mening        — o'z e'lonlarim: «Qaytarildi» / «Bekor qilish»
    Profil        — server manzili, kirish va chiqish
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

import flet as ft

import texts as t
from api_client import ApiError, TopdimApi

# Server bilan bir xil vaqt zonasi: "bugun" ikkalasida bir xil bo'lishi uchun
TASHKENT_TZ = timezone(timedelta(hours=5))
MAX_AGE_DAYS = 365

# Telefonda saqlanadigan sozlamalar kalitlari
PREF_SERVER = "topdim.server_url"
PREF_TOKEN = "topdim.token"

LOGIN_POLL_SECONDS = 2

TAB_FEED, TAB_NEW, TAB_MY, TAB_PROFILE = range(4)

KIND_COLORS = {"lost": ft.Colors.RED_400, "found": ft.Colors.GREEN_600}
KIND_ICONS = {"lost": ft.Icons.SEARCH, "found": ft.Icons.INVENTORY_2_OUTLINED}


def today() -> date:
    return datetime.now(TASHKENT_TZ).date()


class TopdimApp:
    """Butun ilova holati va ekranlari shu klassda."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.prefs = ft.SharedPreferences()
        self.launcher = ft.UrlLauncher()
        self.api = TopdimApi("")
        self.meta: dict = {"categories": [], "places": []}
        self.current_tab = TAB_FEED

        # Qidiruv holati (boshqa bo'limga o'tib qaytganda saqlanib qoladi)
        self.feed_query = ""
        self.feed_category = "all"
        self.feed_page = 1

        # Har bir ekran o'z elementlarini shu ustunga joylaydi
        # STRETCH — maydonlar va tugmalar ekranning to'liq kengligini egallaydi
        self.body = ft.Column(
            expand=True,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    # ------------------------------------------------------------------
    # Ishga tushirish va umumiy yordamchilar
    # ------------------------------------------------------------------
    async def start(self) -> None:
        page = self.page
        page.title = t.APP_TITLE
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
        page.padding = 0
        page.appbar = ft.AppBar(
            title=ft.Text(t.APP_TITLE, weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.Colors.INDIGO,
            color=ft.Colors.WHITE,
        )
        page.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label=t.TAB_FEED),
                ft.NavigationBarDestination(icon=ft.Icons.ADD_BOX_OUTLINED, label=t.TAB_NEW),
                ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT, label=t.TAB_MY),
                ft.NavigationBarDestination(icon=ft.Icons.PERSON_OUTLINE, selected_icon=ft.Icons.PERSON, label=t.TAB_PROFILE),
            ],
            on_change=self.on_tab_change,
        )
        page.add(ft.SafeArea(content=ft.Container(self.body, padding=16), expand=True))

        server = await self.prefs.get(PREF_SERVER) or ""
        token = await self.prefs.get(PREF_TOKEN)
        self.api = TopdimApi(server, token)

        # Server sozlanmagan yoki ishlamayotgan bo'lsa — Profil ekrani
        if server and await self.load_meta():
            await self.show_tab(TAB_FEED)
        else:
            await self.show_tab(TAB_PROFILE)

    async def load_meta(self) -> bool:
        """Kategoriya va joylarni serverdan oladi."""
        try:
            self.meta = await self.api.meta()
            return True
        except ApiError:
            return False

    def set_body(self, controls: list[ft.Control]) -> None:
        self.body.controls = controls
        self.page.update()

    def snack(self, message: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(message)))

    def loading(self) -> None:
        self.set_body([ft.Row([ft.ProgressRing()], alignment=ft.MainAxisAlignment.CENTER)])

    def heading(self, text: str) -> ft.Text:
        return ft.Text(text, size=20, weight=ft.FontWeight.BOLD)

    def options(self, key: str) -> list[ft.DropdownOption]:
        return [ft.DropdownOption(key=o["code"], text=o["label"]) for o in self.meta.get(key, [])]

    async def on_tab_change(self, e: ft.ControlEvent) -> None:
        await self.show_tab(e.control.selected_index)

    async def show_tab(self, index: int) -> None:
        self.current_tab = index
        self.page.navigation_bar.selected_index = index
        screens = {
            TAB_FEED: self.show_feed,
            TAB_NEW: self.show_new_item,
            TAB_MY: self.show_my_items,
            TAB_PROFILE: self.show_profile,
        }
        await screens[index]()

    def need_server(self) -> bool:
        """Server sozlanmagan bo'lsa, tushuntirish chiqaradi."""
        if self.api.base_url:
            return False
        self.set_body([
            ft.Text(t.SERVER_REQUIRED),
            ft.FilledButton(content=t.TAB_PROFILE, on_click=lambda e: self.page.run_task(self.show_tab, TAB_PROFILE)),
        ])
        return True

    def need_login(self) -> bool:
        """Kirilmagan bo'lsa, «Telegram orqali kirish» tugmasini ko'rsatadi."""
        if self.api.token:
            return False
        self.set_body([
            ft.Icon(ft.Icons.LOGIN, size=48, color=ft.Colors.INDIGO),
            ft.Text(t.LOGIN_REQUIRED, size=16),
            ft.FilledButton(content=t.LOGIN_BUTTON, icon=ft.Icons.TELEGRAM, on_click=self.login),
        ])
        return True

    async def handle_error(self, error: ApiError) -> None:
        """401 — token eskirgan: uni o'chirib, qayta kirishni so'raymiz."""
        if error.status == 401 and self.api.token:
            await self.save_token(None)
        self.snack(error.message)

    async def save_token(self, token: str | None) -> None:
        self.api.token = token
        if token:
            await self.prefs.set(PREF_TOKEN, token)
        else:
            await self.prefs.remove(PREF_TOKEN)

    # ------------------------------------------------------------------
    # E'lonlar ro'yxati va qidiruv
    # ------------------------------------------------------------------
    async def show_feed(self) -> None:
        if self.need_server():
            return
        search = ft.TextField(
            value=self.feed_query,
            hint_text=t.SEARCH_HINT,
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.on_search,
        )
        category = ft.Dropdown(
            value=self.feed_category,
            options=[ft.DropdownOption(key="all", text=t.ALL_CATEGORIES), *self.options("categories")],
            on_select=self.on_category,
            expand=True,
        )
        self.feed_results = ft.Column(spacing=8)
        self.set_body([search, ft.Row([category]), self.feed_results])
        await self.load_feed(reset=True)

    async def on_search(self, e: ft.ControlEvent) -> None:
        self.feed_query = e.control.value.strip()
        await self.load_feed(reset=True)

    async def on_category(self, e: ft.ControlEvent) -> None:
        self.feed_category = e.control.value or "all"
        await self.load_feed(reset=True)

    async def load_feed(self, reset: bool) -> None:
        """Qidiruv natijalarini yuklaydi. reset=False — keyingi sahifani qo'shadi."""
        if reset:
            self.feed_page = 1
            self.feed_results.controls = [ft.ProgressRing()]
            self.page.update()
        category = None if self.feed_category == "all" else self.feed_category
        try:
            data = await self.api.items(self.feed_query, category, self.feed_page)
        except ApiError as error:
            self.feed_results.controls = [ft.Text(error.message, color=ft.Colors.ERROR)]
            self.page.update()
            return

        controls = self.feed_results.controls if not reset else []
        controls = [c for c in controls if not isinstance(c, (ft.ProgressRing, ft.OutlinedButton))]
        if reset:
            label = t.FOUND_COUNT.format(total=data["total"]) if data["total"] else t.NOTHING_FOUND
            controls.append(ft.Text(label, color=ft.Colors.ON_SURFACE_VARIANT))
        controls += [self.item_card(item) for item in data["items"]]
        if data["page"] < data["total_pages"]:
            controls.append(ft.OutlinedButton(content=t.LOAD_MORE, on_click=self.load_more))
        self.feed_results.controls = controls
        self.page.update()

    async def load_more(self, e: ft.ControlEvent) -> None:
        self.feed_page += 1
        await self.load_feed(reset=False)

    def item_card(self, item: dict, show_status: bool = False) -> ft.Card:
        """Ro'yxatdagi bitta e'lon."""
        subtitle = f"{t.KIND_LABELS[item['kind']]} · {item['place_label']} · {item['event_date_label']}"
        if show_status:
            subtitle += f"\n{t.STATUS_LABELS[item['status']]}"

        async def open_item(e: ft.ControlEvent) -> None:
            await self.open_item(item["id"])

        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(KIND_ICONS[item["kind"]], color=KIND_COLORS[item["kind"]]),
                title=ft.Text(item["title"], weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                subtitle=ft.Text(subtitle),
                is_three_line=show_status,
                on_click=open_item,
            )
        )

    # ------------------------------------------------------------------
    # E'lon tafsiloti
    # ------------------------------------------------------------------
    async def open_item(self, item_id: int) -> None:
        try:
            item = await self.api.item(item_id)
        except ApiError as error:
            await self.handle_error(error)
            return

        def row(label: str, value: str) -> ft.Column:
            return ft.Column(
                [ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT), ft.Text(value, size=16)],
                spacing=2,
            )

        content: list[ft.Control] = []
        if item["has_photo"]:
            try:
                photo = await self.api.photo(item_id)
                content.append(ft.Image(src=photo, height=220, fit=ft.BoxFit.CONTAIN, border_radius=8))
            except ApiError:
                pass  # rasm yuklanmasa ham e'lonni ko'rsataveramiz
        content += [
            ft.Text(
                t.KIND_LABELS[item["kind"]].upper(),
                color=KIND_COLORS[item["kind"]],
                weight=ft.FontWeight.BOLD,
            ),
            row(t.DETAIL_CATEGORY, item["category_label"]),
            row(t.DETAIL_PLACE, item["place_label"]),
            row(t.DETAIL_DATE[item["kind"]], item["event_date_label"]),
            row(t.DETAIL_DESCRIPTION, item["description"]),
            row(t.DETAIL_STATUS, t.STATUS_LABELS[item["status"]]),
        ]
        if not item["is_mine"]:
            content.append(ft.Text(t.CONTACT_HINT, size=12, italic=True))

        actions: list[ft.Control] = []
        if item["is_mine"] and item["status"] == "active":
            actions += [
                ft.TextButton(content=t.MARK_RETURNED, on_click=self.ask_status(item_id, "returned")),
                ft.TextButton(content=t.CANCEL_ITEM, on_click=self.ask_status(item_id, "cancelled")),
            ]
        actions.append(ft.TextButton(content=t.CLOSE, on_click=lambda e: self.page.pop_dialog()))

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(f"#{item['id']} {item['title']}"),
                content=ft.Column(content, tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
                actions=actions,
                scrollable=True,
            )
        )

    def ask_status(self, item_id: int, status: str):
        """«Qaytarildi» / «Bekor qilish» tugmasi uchun handler yasaydi."""
        question = t.CONFIRM_RETURNED if status == "returned" else t.CONFIRM_CANCEL

        async def confirmed(e: ft.ControlEvent) -> None:
            self.page.pop_dialog()
            try:
                await self.api.set_status(item_id, status)
            except ApiError as error:
                await self.handle_error(error)
                return
            self.snack(t.STATUS_CHANGED)
            await self.show_tab(self.current_tab)

        async def ask(e: ft.ControlEvent) -> None:
            self.page.pop_dialog()
            self.page.show_dialog(
                ft.AlertDialog(
                    content=ft.Text(question),
                    actions=[
                        ft.TextButton(content=t.NO, on_click=lambda e: self.page.pop_dialog()),
                        ft.FilledButton(content=t.YES, on_click=confirmed),
                    ],
                )
            )

        return ask

    # ------------------------------------------------------------------
    # Yangi e'lon
    # ------------------------------------------------------------------
    async def show_new_item(self) -> None:
        if self.need_server() or self.need_login():
            return

        self.form_date = today()
        self.form_kind = ft.SegmentedButton(
            segments=[
                ft.Segment(value="lost", label=ft.Text(t.KIND_LABELS["lost"]), icon=ft.Icon(KIND_ICONS["lost"])),
                ft.Segment(value="found", label=ft.Text(t.KIND_LABELS["found"]), icon=ft.Icon(KIND_ICONS["found"])),
            ],
            selected=["lost"],
        )
        self.form_category = ft.Dropdown(label=t.FIELD_CATEGORY, options=self.options("categories"), expand=True)
        self.form_title = ft.TextField(label=t.FIELD_TITLE, hint_text=t.FIELD_TITLE_HINT, max_length=100)
        self.form_place_note = ft.TextField(
            label=t.FIELD_PLACE_NOTE, hint_text=t.FIELD_PLACE_NOTE_HINT, max_length=100, visible=False
        )
        self.form_place = ft.Dropdown(
            label=t.FIELD_PLACE, options=self.options("places"), on_select=self.on_place_select, expand=True
        )
        self.form_date_label = ft.Text(self.form_date.strftime("%d.%m.%Y"), weight=ft.FontWeight.BOLD)
        self.form_date_choice = ft.SegmentedButton(
            segments=[
                ft.Segment(value="today", label=ft.Text(t.DATE_TODAY)),
                ft.Segment(value="yesterday", label=ft.Text(t.DATE_YESTERDAY)),
                ft.Segment(value="other", label=ft.Text(t.DATE_OTHER)),
            ],
            selected=["today"],
            on_change=self.on_date_choice,
        )
        self.form_description = ft.TextField(
            label=t.FIELD_DESCRIPTION,
            hint_text=t.FIELD_DESCRIPTION_HINT,
            multiline=True,
            min_lines=3,
            max_length=700,
        )
        self.set_body([
            self.heading(t.NEW_TITLE),
            self.form_kind,
            ft.Row([self.form_category]),
            self.form_title,
            ft.Row([self.form_place]),
            self.form_place_note,
            ft.Text(t.FIELD_DATE),
            self.form_date_choice,
            self.form_date_label,
            self.form_description,
            ft.Row([
                ft.Icon(ft.Icons.LOCK_OUTLINE, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(t.PRIVACY_NOTE, size=12, color=ft.Colors.ON_SURFACE_VARIANT, expand=True),
            ]),
            ft.FilledButton(content=t.SUBMIT, icon=ft.Icons.CHECK_CIRCLE, on_click=self.submit_item),
        ])

    def on_place_select(self, e: ft.ControlEvent) -> None:
        # «Boshqa joy» tanlansa — joyni qo'lda yozish maydoni chiqadi
        self.form_place_note.visible = e.control.value == "other"
        self.page.update()

    def on_date_choice(self, e: ft.ControlEvent) -> None:
        choice = e.control.selected[0] if e.control.selected else "today"
        if choice == "other":
            self.page.show_dialog(
                ft.DatePicker(
                    value=self.form_date,
                    first_date=today() - timedelta(days=MAX_AGE_DAYS),
                    last_date=today(),
                    on_change=self.on_date_picked,
                )
            )
            return
        self.set_form_date(today() if choice == "today" else today() - timedelta(days=1))

    def on_date_picked(self, e: ft.ControlEvent) -> None:
        value = e.control.value
        self.set_form_date(value.date() if isinstance(value, datetime) else value)

    def set_form_date(self, value: date) -> None:
        self.form_date = value
        self.form_date_label.value = value.strftime("%d.%m.%Y")
        self.page.update()

    async def submit_item(self, e: ft.ControlEvent) -> None:
        payload = {
            "kind": self.form_kind.selected[0],
            "category": self.form_category.value,
            "title": self.form_title.value,
            "place": self.form_place.value,
            "place_note": self.form_place_note.value if self.form_place.value == "other" else None,
            "event_date": self.form_date.isoformat(),
            "description": self.form_description.value,
        }
        # Oddiy tekshiruvlar shu yerda, qolganini server tekshiradi
        if not payload["category"]:
            self.snack(t.CHOOSE_CATEGORY)
            return
        if not payload["place"]:
            self.snack(t.CHOOSE_PLACE)
            return

        e.control.disabled = True
        self.page.update()
        try:
            item = await self.api.create_item(payload)
        except ApiError as error:
            e.control.disabled = False
            self.page.update()
            await self.handle_error(error)
            return
        self.snack(t.ITEM_CREATED.format(id=item["id"]))
        await self.show_tab(TAB_MY)

    # ------------------------------------------------------------------
    # Mening e'lonlarim
    # ------------------------------------------------------------------
    async def show_my_items(self) -> None:
        if self.need_server() or self.need_login():
            return
        self.loading()
        try:
            data = await self.api.my_items()
        except ApiError as error:
            await self.handle_error(error)
            if not self.api.token:
                self.need_login()
            return
        if not data["items"]:
            self.set_body([self.heading(t.MY_TITLE), ft.Text(t.MY_EMPTY)])
            return
        self.set_body([
            self.heading(t.MY_TITLE),
            *[self.item_card(item, show_status=True) for item in data["items"]],
        ])

    # ------------------------------------------------------------------
    # Profil: server manzili, kirish va chiqish
    # ------------------------------------------------------------------
    async def show_profile(self) -> None:
        self.server_field = ft.TextField(
            label=t.SERVER_TITLE,
            hint_text=t.SERVER_HINT,
            value=self.api.base_url,
            keyboard_type=ft.KeyboardType.URL,
        )
        if self.api.token:
            account = [
                ft.Text(t.LOGGED_IN),
                ft.OutlinedButton(content=t.LOGOUT, icon=ft.Icons.LOGOUT, on_click=self.logout),
            ]
        else:
            account = [ft.FilledButton(content=t.LOGIN_BUTTON, icon=ft.Icons.TELEGRAM, on_click=self.login)]

        self.set_body([
            self.heading(t.TAB_PROFILE),
            *account,
            ft.Divider(),
            self.server_field,
            ft.Text(t.SERVER_HELP, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.FilledButton(content=t.SERVER_SAVE, icon=ft.Icons.CLOUD, on_click=self.save_server),
            ft.Divider(),
            ft.Text(t.ABOUT, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        ])

    async def save_server(self, e: ft.ControlEvent) -> None:
        api = TopdimApi(self.server_field.value, self.api.token)
        try:
            health = await api.health()
        except ApiError as error:
            self.snack(error.message)
            return
        self.api = api
        await self.prefs.set(PREF_SERVER, api.base_url)
        await self.load_meta()
        self.snack(t.SERVER_OK.format(bot=health.get("bot", "")))
        await self.show_profile()

    async def login(self, e: ft.ControlEvent) -> None:
        """Telegram orqali kirish: havolani ochamiz va tasdiqni kutamiz."""
        if self.need_server():
            return
        try:
            start = await self.api.auth_start()
        except ApiError as error:
            self.snack(error.message)
            return

        cancelled = False

        def cancel(e: ft.ControlEvent) -> None:
            nonlocal cancelled
            cancelled = True
            self.page.pop_dialog()

        async def open_telegram(e: ft.ControlEvent | None = None) -> None:
            await self.launcher.launch_url(start["url"], mode=ft.LaunchMode.EXTERNAL_APPLICATION)

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(t.LOGIN_WAITING_TITLE),
                content=ft.Column(
                    [ft.Text(t.LOGIN_WAITING), ft.Row([ft.ProgressRing()], alignment=ft.MainAxisAlignment.CENTER)],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(content=t.LOGIN_OPEN_AGAIN, on_click=open_telegram),
                    ft.TextButton(content=t.CANCEL, on_click=cancel),
                ],
            )
        )
        await open_telegram()

        # Har 2 soniyada serverdan so'raymiz: foydalanuvchi botda tasdiqladimi?
        deadline = asyncio.get_running_loop().time() + start["expires_in"]
        while not cancelled and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(LOGIN_POLL_SECONDS)
            if cancelled:
                return
            try:
                token = await self.api.auth_check(start["code"])
            except ApiError as error:
                if error.status == 410:  # kod eskirgan
                    break
                continue  # tarmoq uzilishi — keyingi urinish
            if token:
                await self.save_token(token)
                self.page.pop_dialog()
                self.snack(t.LOGIN_SUCCESS)
                await self.show_tab(self.current_tab)
                return

        if not cancelled:
            self.page.pop_dialog()
            self.snack(t.LOGIN_EXPIRED)

    async def logout(self, e: ft.ControlEvent) -> None:
        try:
            await self.api.logout()
        except ApiError:
            pass  # server bilan aloqa bo'lmasa ham telefondan tokenni o'chiramiz
        await self.save_token(None)
        self.snack(t.LOGGED_OUT)
        await self.show_profile()


async def main(page: ft.Page) -> None:
    await TopdimApp(page).start()


if __name__ == "__main__":
    ft.run(main)
