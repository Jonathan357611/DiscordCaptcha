import discord
from discord.ext import commands
from discord.utils import get
from io import BytesIO
import helper
import time

data = helper.load_data()

TOKEN = data["settings"]["token"]
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="v!", intents=intents)
bot.remove_command("help")


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    await bot.change_presence(activity=discord.Game("v!help"))


@bot.event
async def on_member_join(member):
    data = helper.load_data()

    guild_id = str(member.guild.id)
    if guild_id not in list(data["servers"].keys()):
        await member.guild.create_role(name="Verified")
        data["servers"][guild_id] = {
            "verified": [],
            "captcha_length": data["settings"]["default_length"],
            "message": "Hey <user>, welcome to <servername>!\nPlease complete the Captcha to verify yourself!",
            "ban_after": data["settings"]["ban_after"],
            "ignore_cases": True,
        }
        helper.write_data(data)
        data = helper.load_data()

    # Fill in variables
    msg = data["servers"][guild_id]["message"]
    msg = msg.replace("<user>", member.mention)
    msg = msg.replace("<servername>", member.guild.name)
    await member.send(msg)  # Send message

    await member.send(
        f"You have to be done <t:{round(time.time()) + data['settings']['time']}:R>"
    )

    # Get Captcha
    captcha = helper.generate_captcha(data["servers"][guild_id]["captcha_length"])
    captcha_img = captcha[0]
    captcha_text = captcha[1]
    await member.send(file=discord.File(fp=captcha_img, filename="image.png"))

    data["pending"][str(member.id)] = {
        "server_id": guild_id,
        "captcha": captcha_text,
        "try_count": 0,
        "request_time": time.time(),
    }

    helper.write_data(data)

    await bot.process_commands(member)


@bot.event
async def on_message(ctx):
    if not ctx.author.bot:
        if isinstance(ctx.channel, discord.channel.DMChannel):
            data = helper.load_data()

            if (
                str(ctx.author.id) in data["pending"].keys()
                and data["pending"][str(ctx.author.id)]["request_time"]
                > time.time() - data["settings"]["time"]
            ):
                msg = ctx.content
                captcha_text = data["pending"][str(ctx.author.id)]["captcha"]
                guild_id = data["pending"][str(ctx.author.id)]["server_id"]

                if data["servers"][guild_id]["ignore_cases"] == True:
                    msg = msg.lower()
                    captcha_text = captcha_text.lower()

                if msg == captcha_text:
                    await ctx.add_reaction("✅")

                    data["servers"][str(guild_id)]["verified"].append(
                        str(ctx.author.id)
                    )
                    guild = bot.get_guild(int(guild_id))
                    for member in guild.members:
                        if member.id == ctx.author.id:
                            role = discord.utils.get(guild.roles, name="Verified")
                            await member.add_roles(role)

                    del data["pending"][str(ctx.author.id)]
                else:
                    await ctx.add_reaction("❌")
                    data["pending"][str(ctx.author.id)]["try_count"] += 1
                    if (
                        data["pending"][str(ctx.author.id)]["try_count"]
                        >= data["servers"][str(guild_id)]["ban_after"]
                    ):
                        guild = bot.get_guild(int(guild_id))
                        for member in guild.members:
                            if member.id == ctx.author.id:
                                await member.send(
                                    f"Sorry, but you have been banned for taking more than {data['servers'][str(guild_id)]['ban_after']} tries on the captcha!"
                                )
                                await member.ban(
                                    reason="Took too many tries on the Captcha!"
                                )
                                del data["pending"][str(ctx.author.id)]

                    helper.write_data(data)
            else:
                await ctx.author.send("There is no active Captcha.")
                if str(ctx.author.id) in data["pending"].keys():
                    del data["pending"][str(ctx.author.id)]

            helper.write_data(data)

        else:
            ...
    await bot.process_commands(ctx)


@bot.command(name="length", help=f"Set captcha length")
@commands.has_permissions(administrator=True)
async def set_captcha_length(ctx, new_length: int):
    data = helper.load_data()
    guild_id = str(ctx.guild.id)

    if new_length >= int(data["settings"]["min_length"]) and new_length <= int(
        data["settings"]["max_length"]
    ):
        data["servers"][guild_id]["captcha_length"] = new_length
        await ctx.send(f"Updated Captcha-length to {new_length} chars!")
    else:
        await ctx.send(
            f'Please choose a value between {data["settings"]["min_length"]} and {data["settings"]["max_length"]}!'
        )

    helper.write_data(data)


@bot.command(name="ban-after", help=f"Set amount of tries before banning user.")
@commands.has_permissions(administrator=True)
async def set_captcha_length(ctx, new_amount: int):
    data = helper.load_data()
    guild_id = str(ctx.guild.id)

    data["servers"][guild_id]["ban_after"] = new_amount
    await ctx.send(f"Updated Try-amoung to {new_amount} before banning user!")

    helper.write_data(data)


@bot.command(
    name="correct-casing",
    help=f"Change if the user has to use the correct letter-casing, set to 'yes' or 'no'",
)
@commands.has_permissions(administrator=True)
async def set_captcha_length(ctx, need_casing: str):
    data = helper.load_data()
    guild_id = str(ctx.guild.id)

    if need_casing.lower() == "no" or need_casing.lower() == "n":
        data["servers"][guild_id]["ignore_cases"] = True
        await ctx.send(f"Updated, the user can now ignore letter-casing.")
    else:
        data["servers"][guild_id]["ignore_cases"] = False
        await ctx.send(f"Updated, the user has to use the correct letter-casing!")

    helper.write_data(data)


@bot.command(name="help")
async def help(ctx):
    await ctx.send(
        """```Captcha-Help
v!length <length>  -  set new captcha lenght
v!ban-after <amount>  -  Amount of tries a user gets before getting banned
v!correct-casing <y|n>  -  If the user has to use the same letter-casing as in the Captcha
v!message <text>  -  Message to send the user when verifying, can use variables '<user>' and '<servername>', which will get filled in.
```"""
    )


bot.run(TOKEN)
