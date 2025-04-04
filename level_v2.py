import discord
from discord.ext import commands
import time
import json
import os
from discord import app_commands
from discord.ui import Button, View

# ボットの設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容を読み取るため
intents.voice_states = True     # ボイスチャンネルの状態を監視するため
intents.members = True          # サーバーメンバーリストを取得するため
bot = commands.Bot(command_prefix="!", intents=intents)

# ユーザーデータを保存するファイル
DATA_FILE = r"C:\Users\Owner\Desktop\level_bungu\user_data.json"

# 付与したいロールのID
ROLE_ID = 1344295612165656576

# ユーザーデータをファイルから読み込む関数
def load_user_data():
    # ファイルが存在しない場合、自動で新規作成する
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)  # 空のデータを保存
        return {}
    
    with open(DATA_FILE, "r") as f:
        try:
            # ファイルの内容が空でないかチェック
            file_content = f.read().strip()
            if not file_content:
                # 空のファイルの場合
                return {}
            else:
                return json.loads(file_content)  # 正常なJSONとして読み込む
        except json.JSONDecodeError:
            # 不正なJSONがある場合は空の辞書を返す
            print("JSONの読み込みエラー: 空の辞書を返します")
            return {}

# ユーザーデータをファイルに保存する関数
def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ユーザーにロールを付与する関数
async def assign_role_to_member(member):
    # ボットは対象外
    if member.bot:
        return
    
    try:
        # 指定されたロールID
        role = member.guild.get_role(ROLE_ID)
        
        if role is None:
            print(f"ロールID {ROLE_ID} が見つかりませんでした。")
            return
            
        # 既にそのロールを持っているかチェック
        if role in member.roles:
            return
            
        # ロールを付与
        await member.add_roles(role)
        print(f"{member.name} にロール {role.name} を付与しました。")
    except Exception as e:
        print(f"ロール付与エラー ({member.name}): {e}")

# ボット起動時の処理
@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    
    try:
        # sync コマンドを同期
        await bot.tree.sync()
        print("コマンドを同期しました")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")
    
    # ボットが起動した時にサーバー内のすべてのメンバーを記録
    user_data = load_user_data()
    
    # サーバーごとに処理
    for guild in bot.guilds:
        print(f"サーバー {guild.name} のメンバーを処理中...")
        for member in guild.members:
            if member.bot:
                continue
            
            # ユーザーデータに存在しないユーザーは初期化
            if str(member.id) not in user_data:
                user_data[str(member.id)] = {"messages_sent": 0, "voice_time": 0, "last_connect_time": None}
            
            # ボイスチャットに参加している場合、接続時間のカウントを開始
            if member.voice and member.voice.channel:
                user_data[str(member.id)]["last_connect_time"] = time.time()
                
            # ロール付与処理を実行
            await assign_role_to_member(member)
    
    # ユーザーデータをファイルに保存
    save_user_data(user_data)

# 新規メンバー参加時の処理
@bot.event
async def on_member_join(member):
    # ユーザーデータを読み込む
    user_data = load_user_data()
    
    # 新規ユーザーを初期化
    if str(member.id) not in user_data:
        user_data[str(member.id)] = {"messages_sent": 0, "voice_time": 0, "last_connect_time": None}
        save_user_data(user_data)
    
    # ロールを付与
    await assign_role_to_member(member)

# メッセージ送信時の処理
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ユーザーデータを読み込む
    user_data = load_user_data()

    # ユーザーのメッセージ数をカウント
    if str(message.author.id) not in user_data:
        user_data[str(message.author.id)] = {"messages_sent": 0, "voice_time": 0, "last_connect_time": None}

    user_data[str(message.author.id)]["messages_sent"] += 1
    
    # ユーザーデータをファイルに保存
    save_user_data(user_data)

    await bot.process_commands(message)  # コマンドを処理する

# ボイスチャット接続時の処理
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # ユーザーデータを読み込む
    user_data = load_user_data()

    user_id = str(member.id)
    
    if user_id not in user_data:
        user_data[user_id] = {"messages_sent": 0, "voice_time": 0, "last_connect_time": None}
    
    # ユーザーがボイスチャネルに接続したとき
    if after.channel is not None and before.channel is None:
        user_data[user_id]["last_connect_time"] = time.time()  # 現在の時刻を記録

    # ユーザーがボイスチャネルを切断したとき
    if after.channel is None and before.channel is not None:
        if user_data[user_id]["last_connect_time"]:
            # 接続していた時間を計算して記録
            time_connected = time.time() - user_data[user_id]["last_connect_time"]
            user_data[user_id]["voice_time"] += time_connected / 60  # 時間を分単位に変換
            user_data[user_id]["last_connect_time"] = None

    # ユーザーデータをファイルに保存
    save_user_data(user_data)

# ページネーション用のViewクラス
class PaginationView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=60)  # 60秒でボタンは非アクティブになる
        self.pages = pages
        self.author_id = author_id
        self.current_page = 0
        self.total_pages = len(pages)
        
        # 最初からボタンを追加
        self.update_buttons()
        
    def update_buttons(self):
        # ボタンをクリア
        self.clear_items()
        
        # 前へボタン (現在最初のページでない場合に表示)
        if self.current_page > 0:
            previous_button = Button(label="◀ 前へ", style=discord.ButtonStyle.primary)
            previous_button.callback = self.previous_page
            self.add_item(previous_button)
        
        # ページ番号表示
        page_indicator = Button(
            label=f"{self.current_page + 1}/{self.total_pages}", 
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.add_item(page_indicator)
        
        # 次へボタン (現在最後のページでない場合に表示)
        if self.current_page < self.total_pages - 1:
            next_button = Button(label="次へ ▶", style=discord.ButtonStyle.primary)
            next_button.callback = self.next_page
            self.add_item(next_button)
    
    async def previous_page(self, interaction):
        # インタラクションを行ったユーザーがコマンド実行者と同じか確認
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
            return
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)
    
    async def next_page(self, interaction):
        # インタラクションを行ったユーザーがコマンド実行者と同じか確認
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
            return
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(content=self.pages[self.current_page], view=self)
    
    async def on_timeout(self):
        # タイムアウト時にボタンを無効化
        for item in self.children:
            item.disabled = True
        
        # メッセージを編集してボタンを無効化
        message = self.message
        if message:
            try:
                await message.edit(view=self)
            except:
                pass

# ロール付与コマンド（手動でロールを付与する場合に使用）
@bot.hybrid_command(name="assign_role", description="指定されたロールをサーバーの全メンバーに付与します")
@commands.has_permissions(administrator=True)  # 管理者権限を持つユーザーのみ実行可能
async def assign_role(ctx):
    await ctx.defer()  # 処理に時間がかかる可能性があるため、応答を遅延
    
    success_count = 0
    fail_count = 0
    
    for member in ctx.guild.members:
        if member.bot:
            continue
            
        try:
            await assign_role_to_member(member)
            success_count += 1
        except Exception:
            fail_count += 1
    
    await ctx.send(f"ロール付与処理完了: 成功 {success_count}件、失敗 {fail_count}件")

# 通常のコマンド (!) とスラッシュコマンド (/) の両方をサポート
@bot.hybrid_command(name="level", description="ユーザーのレベルリーダーボードを表示")
async def level(ctx):
    if not ctx.guild:
        await ctx.send("このコマンドはサーバー内でのみ使用できます。")
        return
        
    user_data = load_user_data()
    
    # ユーザーIDとユーザー名のマッピングを作成
    user_cache = {}
    for member in ctx.guild.members:
        user_cache[str(member.id)] = member.name
    
    # メッセージ数とボイスチャット接続時間が記録されているユーザーのリストを作成
    leaderboard_entries = []
    for user_id, data in user_data.items():
        # データが記録されているすべてのユーザーをリストに追加
        messages_sent = data.get("messages_sent", 0)
        voice_time = data.get("voice_time", 0)
        
        # キャッシュからユーザー名を取得、なければDiscord APIで検索
        if user_id in user_cache:
            user_name = user_cache[user_id]
        else:
            try:
                # フェッチできない場合はIDを表示
                user = await bot.fetch_user(int(user_id))
                user_name = user.name
            except Exception as e:
                print(f"ユーザー取得エラー {user_id}: {e}")
                user_name = f"不明なユーザー ({user_id})"
        
        # 時間単位に変換（分から時間へ）
        voice_hours = voice_time / 60
        
        # リーダーボードに追加
        leaderboard_entries.append((user_name, voice_hours, messages_sent))
    
    # VC時間の長い順にソート
    leaderboard_entries.sort(key=lambda x: x[1], reverse=True)
    
    # リーダーボードを表示用に整形
    if leaderboard_entries:
        # 1ページに表示するユーザー数
        users_per_page = 10
        
        # ページを作成
        pages = []
        
        # 複数ページに分割
        for i in range(0, len(leaderboard_entries), users_per_page):
            page_entries = leaderboard_entries[i:i+users_per_page]
            page_content = "\n".join([
                f"{j+1+i}. {name}  🎤 {hours:.2f}時間  💬 {msgs}回" 
                for j, (name, hours, msgs) in enumerate(page_entries)
            ])
            pages.append(f"**レベルリーダーボード** (ページ {len(pages)+1}/{(len(leaderboard_entries)-1)//users_per_page+1}):\n{page_content}")
        
        # ページネーションViewを作成
        pagination_view = PaginationView(pages, ctx.author.id)
        
        # 最初のページを送信し、メッセージを保存
        message = await ctx.send(pages[0], view=pagination_view)
        pagination_view.message = message
    else:
        await ctx.send("データが記録されているユーザーがいません。")

# ボットを実行
bot.run("")
