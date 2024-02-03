import discord
from discord.ext import commands
from datetime import datetime
import sqlite3
import asyncio


# Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# Create bot instance with intents
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')
bot.help_command = commands.DefaultHelpCommand(no_category='Commands')

# Connect to SQLite database
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()

# Create a table for user points
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_points (
        user_id INTEGER PRIMARY KEY,
        points REAL
    )
''')


# Create a table for salary history
cursor.execute('''
    CREATE TABLE IF NOT EXISTS salary_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        amount REAL,
        command TEXT,
        executor INTEGER,
        current_salary REAL,
        month TEXT,  -- Thêm cột mới để lưu trữ tháng
        FOREIGN KEY (user_id) REFERENCES user_points(user_id)
    )
''')


conn.commit()

# Function to add or subtract points and update history
def update_points(user_id, amount, command, executor_id, target_month):
    current_month = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Insert or update user points in the database
    cursor.execute('INSERT OR IGNORE INTO user_points (user_id, points) VALUES (?, ?)', (user_id, 0.0))
    cursor.execute('UPDATE user_points SET points = points + ? WHERE user_id = ?', (amount, user_id))

    # Insert salary change into the salary history
    cursor.execute('''
        INSERT INTO salary_history (user_id, timestamp, amount, command, executor, current_salary, month)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, current_month, amount, command, executor_id, cursor.execute('SELECT points FROM user_points WHERE user_id = ?', (user_id,)).fetchone()[0], target_month))
    # ...
    conn.commit()




# Define the role IDs for each command
role_ids = {
    'a': [1202583369708474368],  # Role Admin
    'm': [1202583369708474368],  # Role Ad
    'undo': [1202583369708474368],  # Role Ad
    'reset': [1202589756647673856],  # Boss
    'view': [1203246669630672906, 1202583369708474368]  # Role staff
}

# Check if the user has the correct role for a specific command
def has_correct_role(ctx, command_name):
    allowed_roles = [discord.utils.get(ctx.guild.roles, id=role_id) for role_id in role_ids.get(command_name, [])]
    return any(role in ctx.author.roles for role in allowed_roles)

# Check if the user has the required permissions
def has_permissions(ctx, command_name):
    # Customize this function based on your permissions requirements
    if command_name == 'a':
        return ctx.author.guild_permissions.manage_messages
    elif command_name == 'm':
        return ctx.author.guild_permissions.manage_messages
    elif command_name == 'undo':
        return ctx.author.guild_permissions.manage_messages
    elif command_name == 'view':
        return True  # No specific permissions required for view command
    return True

# Check if the user is spamming commands
def is_spamming(ctx, command_name):
    # Customize this function based on your spamming prevention requirements
    return False  # Replace this with your spamming check logic

# Send a warning message to the user
async def send_warning(ctx, message):
    await ctx.send(f":warning: **{message}**")

@bot.command(name='a')
@commands.check(lambda ctx: has_correct_role(ctx, 'a') and has_permissions(ctx, 'a') and not is_spamming(ctx, 'a'))
async def add_points(ctx, user: discord.Member, number: float, target_month: str = None, *, timestamp: str = None):
    target_month = target_month or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp = timestamp or target_month

    update_points(user.id, number, 'add', ctx.author.id, target_month)
    # Fetch the current salary after the update
    current_salary = cursor.execute('SELECT points FROM user_points WHERE user_id = ?', (user.id,)).fetchone()[0]

    # Format target_month to display as "tháng [number] năm [number]"
    formatted_target_month = datetime.strptime(target_month, '%Y-%m-%d %H:%M:%S').strftime('tháng %m %Y')

    # Send messages
    await ctx.send(f"Lương {formatted_target_month} của {user.mention} là {current_salary} K (Trước đó: {current_salary - number} K).")
    await user.send(f"Bạn đã được thêm {number} K vào lương {formatted_target_month}. Lương hiện tại của bạn là {current_salary} K.")

@bot.command(name='m')
@commands.check(lambda ctx: has_correct_role(ctx, 'm') and has_permissions(ctx, 'm') and not is_spamming(ctx, 'm'))
async def minus_points(ctx, user: discord.Member, number: float, target_month: str = None, *, timestamp: str = None):
    target_month = target_month or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp = timestamp or target_month

    update_points(user.id, -number, 'minus', ctx.author.id, target_month)
    # Fetch the current salary after the update
    current_salary = cursor.execute('SELECT points FROM user_points WHERE user_id = ?', (user.id,)).fetchone()[0]
    # Send messages
    # Format target_month to display as "tháng [number] năm [number]"
    formatted_target_month = datetime.strptime(target_month, '%Y-%m-%d %H:%M:%S').strftime('tháng %m  %Y')
    
    # Send messages
    await ctx.send(f"Lương {formatted_target_month} của {user.mention} là {current_salary} K (Trước đó: {current_salary - number} K).")
    await user.send(f"Bạn đã được thêm {number} K vào lương {formatted_target_month}. Lương hiện tại của bạn là {current_salary} K.")

# ... (code khác)



@bot.command(name='reset')
@commands.check(lambda ctx: has_correct_role(ctx, 'reset') and has_permissions(ctx, 'reset') and not is_spamming(ctx, 'reset'))
async def reset_points(ctx, user: discord.Member):
    current_month = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Xóa thông tin lương của người dùng trong cơ sở dữ liệu
    cursor.execute('DELETE FROM user_points WHERE user_id = ?', (user.id,))
    cursor.execute('DELETE FROM salary_history WHERE user_id = ?', (user.id,))
    
    conn.commit()

    # Gửi thông báo lên kênh chat
    await ctx.send(f"Lương của {user.mention} đã được reset.")

    # Gửi tin nhắn riêng cho người dùng được reset
    await user.send(f"Lương của bạn đã được reset. Mọi thông tin lương trước đó đã bị xóa.")

@bot.command(name='undo')
@commands.check(lambda ctx: has_correct_role(ctx, 'undo') and has_permissions(ctx, 'undo') and not is_spamming(ctx, 'undo'))
async def undo_last_operation(ctx, user: discord.Member, target_month: str = None):
    target_month = target_month or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Lấy ra lịch sử lương của người dùng từ cơ sở dữ liệu
    history = cursor.execute('SELECT * FROM salary_history WHERE user_id = ? AND month = ? ORDER BY timestamp DESC', (user.id, target_month)).fetchall()
    
    if history:
        amount = history['amount']
        command = history['command']

        if command == 'add':
            cursor.execute('UPDATE user_points SET points = points - ? WHERE user_id = ?', (amount, user.id))
        elif command == 'minus':
            cursor.execute('UPDATE user_points SET points = points + ? WHERE user_id = ?', (amount, user.id))

        # Xóa lịch sử lương cuối cùng của người dùng
        cursor.execute('DELETE FROM salary_history WHERE user_id = ? AND timestamp = ?', (user.id, history['timestamp']))
        
        conn.commit()

        await ctx.send(f"Undo thành công! Lương của {user.mention} đã được khôi phục.")
    else:
        await ctx.send(f"{user.mention} không có lệnh nào để undo.")


@bot.command(name='view')
@commands.check(lambda ctx: has_correct_role(ctx, 'view') and has_permissions(ctx, 'view') and not is_spamming(ctx, 'view'))
async def view_salary_history(ctx, user: discord.Member):
    history = cursor.execute('SELECT * FROM salary_history WHERE user_id = ? ORDER BY timestamp DESC', (user.id,)).fetchall()
    if history:
        message = f"Lịch sử lương của {user.mention}:\n"
        for entry in history:
            timestamp, amount, command, executor_id, current_salary, target_month = entry[2:8]
            formatted_target_month = datetime.strptime(target_month, '%Y-%m-%d %H:%M:%S').strftime('tháng %m %Y')
            message += f"{formatted_target_month}: {command} {amount} K (Tổng lương: {current_salary} K)\n"
            
        # Gửi thông điệp riêng tư về lịch sử lương
        await user.send(message)
        await ctx.send(f"Lịch sử lương đã được gửi riêng tư cho {user.mention}.")
    else:
        await ctx.send(f"{user.mention} không có lịch sử lương.")


@bot.command(name='p')
@commands.check(lambda ctx: has_correct_role(ctx, 'view') and has_permissions(ctx, 'view') and not is_spamming(ctx, 'view'))
async def view_profile(ctx, user: discord.Member = None):
    user = ctx.author
    history = cursor.execute('SELECT * FROM salary_history WHERE user_id = ? ORDER BY timestamp DESC', (user.id,)).fetchall()
    if history:
        message = f"Lịch sử lương của {user.mention}:\n"
        for entry in history:
            timestamp, amount, command, executor_id, current_salary, target_month = entry[2:8]
            formatted_target_month = datetime.strptime(target_month, '%Y-%m-%d %H:%M:%S').strftime('tháng %m %Y')
            message += f"{formatted_target_month}: {command} {amount} K (Tổng lương: {current_salary} K)\n"
            
        # Gửi thông điệp riêng tư về lịch sử lương
        await ctx.author.send(message)
        await ctx.send("Lịch sử lương đã được gửi riêng tư cho bạn.")
    else:
        await ctx.send(f"{user.mention} không có lịch sử lương.")



# Run the bot
bot.run('MTIwMzQzNzg1ODY3Nzg1MDIzMg.GXRUPF.bKWJJrAgrN-Sd4t4nbq2RLHqSDZ4HviEgXkG0Y')