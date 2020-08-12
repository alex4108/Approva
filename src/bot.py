# bot.py
import os

import discord
from dotenv import load_dotenv
from discord.ext import commands
import logging as log
log.basicConfig(level=log.INFO)
import sqlite3

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
global db
global db_cursor
global discord

DB_NAME = "sqlite"
db_path = os.path.join(os.path.abspath(os.getcwd()), DB_NAME + ".db")
db = sqlite3.connect(db_path)
db_cursor = db.cursor()
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS approval_pubrole (
        guild_id TEXT,
        pubrole TEXT PRIMARY KEY
    )
""")

db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS approval_channel (
        guild_id TEXT,
        channel TEXT PRIMARY KEY
    )
""")

db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS approval_role (
        guild_id TEXT,
        role TEXT PRIMARY KEY
    )
""")

db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS approval_pubchannel (
        guild_id TEXT,
        pubchannel TEXT PRIMARY KEY
    )
""")

db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_approvals (
        guild_id TEXT,
        message_id TEXT PRIMARY KEY,
        member_id TEXT
    )
""")

bot = commands.Bot(command_prefix='*')


def is_owner(member):
    """ Boolean return if the person is guild owner or not """
    log.info("Owner check: " + member.name + "(" + str(member.id) + ")")
    if member.id == member.guild.owner.id:
        return True
    else:
        return False

def resolve_role(guild, role_id):
    """ Resolves a Discord ID to a role object """
    global discord
    roleObj = discord.utils.get(guild.roles, id=role_id)
    return roleObj

def resolve_channel(guild, channel_id):
    """ Resolves a Discord ID to a channel object """
    global discord
    channelObj = discord.utils.get(guild.text_channels, id=channel_id)
    return channelObj

def validate_guild_config(guild):
    config = get_guild_config(guild)
    for c in config:
        if c == None:
            return False

    return True


def get_guild_config(guild): 
    """ Returns related config for the guild """
    global discord
    global db_cursor

    
    db_cursor.execute("select pubrole from approval_pubrole where guild_id = \"" + str(guild.id) + "\" ")
    approval_pubrole = db_cursor.fetchall()

    db_cursor.execute("select pubchannel from approval_pubchannel where guild_id = \"" + str(guild.id) + "\" ")
    approval_pubchannel = db_cursor.fetchall()

    db_cursor.execute("select role from approval_role where guild_id = \"" + str(guild.id) + "\" ")
    approval_channel = db_cursor.fetchall()

    db_cursor.execute("select channel from approval_channel where guild_id = \"" + str(guild.id) + "\" ")
    approval_role = db_cursor.fetchall()

    try:
        approval_role = approval_role[0][0]
        approval_role = resolve_role(guild, int(approval_role))
    except Exception:
        approval_role = None

    try:
        approval_pubchannel = approval_pubchannel[0][0]
        approval_pubchannel = resolve_channel(guild, int(approval_pubchannel))
    except Exception:
        approval_pubchannel = None

    try:
        approval_channel = approval_channel[0][0]
        approval_channel = resolve_channel(guild, int(approval_channel))
    except Exception:
        approval_channel = None

    try:
        approval_pubrole = approval_pubrole[0][0]
        approval_pubrole = resolve_role(guild, int(approval_pubrole))
    except Exception:
        approval_pubrole = None

    return { 'pubrole': approval_pubrole, 'pubchannel': approval_pubchannel, 'channel': approval_channel, 'role': approval_role}


@bot.event
async def on_ready():
    log.info(f'Bot is online!')

@bot.event
async def on_member_join(member):
    global db_cursor

    # Break if not configured
    if (not validate_guild_config(member.guild)):
        log.info("Skipping join event because Guild " + member.guild.name + " is not configured")
        return
        
    config = get_guild_config(member.guild)
    # Send message to pubchannel
    log.info("Processing approval for " + member.name)
    await approval_pubchannel.send("Welcome <@" + str(member.id) + "> - You have been placed in queue for approval to more channels.  You may use public channels until you are approved as " + str(config['pubrole']) + "." ) 
    
    # Send a message to moderators room, if configured
    approvalMsg = await approval_channel.send(member.name + " has joined the server.  You may grant them access to all rooms by clicking the check under this message. ")
    await approvalMsg.add_reaction("\u2705")
    db_cursor.execute(" INSERT INTO pending_approvals (guild_id, member_id, message_id) VALUES (" + str(member.guild.id) + ", " + str(member.id) + ", " + str(approvalMsg.id) + ") ")
    pass

@bot.event
async def on_reaction_add(reaction, user):
    global db_cursor

    if (not validate_guild_config(reaction.message.guild)):
        log.info("Skipping reaction event because Guild " + reaction.message.guild.name + " is not configured")
        return

    msg = reaction.message
    log.info("Received Reaction " + reaction.emoji + " on message " + str(msg.id))
    approved = False
    db_cursor.execute("SELECT * FROM pending_approvals WHERE guild_id = " + str(reaction.message.guild.id) + " AND message_id = " + str(msg.id) + " ")
    pending_approvals = db_cursor.fetchall()
    log.debug(pending_approvals)
    for approval in pending_approvals:
        
        if msg.id == approval['message_id'] and reaction.emoji == "\u2705":
            log.debug("Getting Member")
            # Get member
            for member in msg.guild.members:
                if approval['member_id'] == member.id:
                    log.info("Got member")
                    thisMember = member
                
            # Set Role
            for approverRole in user.roles:
                log.info("Checking if " + user.name + " has role " + str(approval_role))
                log.debug(user)
                log.debug(approverRole)
                if approverRole == approval_role:
                    approved = True
                    log.info("Approved!")

            if not approved:
                log.info("Denied approval for " + thisMember.name + " by " + user.name + " because insufficient role")
                return

            await thisMember.add_roles(approval_pubrole)
            # Announce
            await approval_channel.send("<@" + str(user.id) + "> approved <@" + thisMember.id + ">")
            db_cursor.execute("DELETE FROM pending_approvals WHERE id = " + approval['id'] + " ")
            pass
    


@bot.command()
async def setApprovalChannel(ctx, channelName):
    global db_cursor
    global db

    if not is_owner(ctx.author):
        log.info("Denied setApprovalChannel to " + ctx.author.name)
        await ctx.send("Denied because you're not my owner!")
        return


    try: 
        log.debug("Approval Channel: " + channelName)
        approval_channel = discord.utils.get(ctx.guild.text_channels, name=channelName) 
        if (approval_channel is None):
            await ctx.send("I was unable to locate a channel by that name.  Please try again")
            return
        
        try:
            log.info("Saving Approval Channel " + str(approval_channel.id) + " for guild " + str(ctx.guild.id) ) 
            db_cursor.execute("insert or replace into approval_channel (guild_id, channel) values (\"" + str(ctx.guild.id) + "\", \"" + str(approval_channel.id) + "\")")
            db.commit()    
            await ctx.send("Set approval channel: " + str(approval_channel.name))
            pass

        except Exception as e:
            log.error(e)
            await ctx.send("There was an error saving to the database.  Please alert my maintainer!")
            return
            
    except discord.DiscordException as e:
        log.error(e)
        await ctx.send("There was an exception trying to get the approval channel")
        pass

    

@bot.command()
async def setApprovalRole(ctx, roleName):
    global db_cursor
    global db
    
    if not is_owner(ctx.author):
        log.info("Denied setApprovalRole to " + ctx.author.name)
        await ctx.send("Denied because you're not my owner!")
        return


    try: 
        log.debug("Approval Role: " + roleName)
        approval_role = discord.utils.get(ctx.guild.roles, name=roleName) 
        log.debug(approval_role)
        if (approval_role is None):
            await ctx.send("I was unable to locate a role by that name.  Please try again")
            return

        try:        
            log.info("Saving Approval Role " + str(approval_role.id) + " for guild " + str(ctx.guild.id) ) 
            db_cursor.execute("insert or replace into approval_role (guild_id, role) values (\"" + str(ctx.guild.id) + "\", \"" + str(approval_role.id) + "\")")
            db.commit()    
            await ctx.send("Set approval role: " + approval_role.name)
            pass
    
        except Exception as e:
            log.error(e)
            await ctx.send("There was an error saving to the database.  Please alert my maintainer!")
            return

    except discord.DiscordException as e:
        log.error(e)
        await ctx.send("There was an exception trying to get the approval channel")
        pass

@bot.command()
async def setPublicChannel(ctx, channelName):
    global db_cursor
    global db
    
    if not is_owner(ctx.author):
        log.info("Denied setPublicChannel to " + ctx.author.name)
        await ctx.send("Denied because you're not my owner!")
        return

    # Get the channel ID
    try: 
        approval_pubchannel = discord.utils.get(ctx.guild.text_channels, name=channelName)
        log.debug(approval_pubchannel)
        if (approval_pubchannel is None):
            await ctx.send("I was unable to locate a channel by that name.  Please try again")
            return
        try:
            log.info("Saving Public Channel " + str(approval_pubchannel.id) + " for guild " + str(ctx.guild.id) ) 
            db_cursor.execute("insert or replace into approval_pubchannel (guild_id, pubchannel) values (\"" + str(ctx.guild.id) + "\", \"" + str(approval_pubchannel.id) + "\")")
            db.commit()
            await ctx.send("Set public channel: " + approval_pubchannel.name)
            pass
    
        except Exception as e:
            log.error(e)
            await ctx.send("There was an error saving to the database.  Please alert my maintainer!")
            return

    except discord.DiscordException as e:
        log.error(e)
        await ctx.send("There was an exception trying to get the approval channel")
        return
    
    

@bot.command()
async def setPublicRole(ctx, roleName):
    global db_cursor
    global db
    
    if not is_owner(ctx.author):
        log.info("Denied setPublicRole to " + ctx.author.name)
        await ctx.send("Denied because you're not my owner!")
        return


    try:
        approval_pubrole = discord.utils.get(ctx.guild.roles, name=roleName)
        log.debug(approval_pubrole)
        if (approval_pubrole is None):
            await ctx.send("I was unable to locate a role by that name.  Please try again")
            return
    
        try:
            log.info("Saving Public Role " + str(approval_pubrole.id) + " for guild " + str(ctx.guild.id) )
            db_cursor.execute("insert or replace into approval_pubrole (guild_id, pubrole) values (\"" + str(ctx.guild.id) + "\", \"" + str(approval_pubrole.id) + "\")")
            db.commit()
            await ctx.send("Set public role: " + approval_pubrole.name)
            pass
        except Exception as e:
            log.error(e)
            await ctx.send("There was an error saving to the database.  Please alert my maintainer!")
            return
    
    except discord.DiscordException as e:
        log.error(e)
        await ctx.send("There was an exception trying to get the approval channel")
        return
    
    

@bot.command()
async def ping(ctx):
    await ctx.send('pong')
    pass

@bot.command()
async def showConfig(ctx):

    config = get_guild_config(ctx.guild)
    log.debug(config)
    await ctx.send("Public Role: " + str(config['pubrole']) + "\nPublic Channel: " + str(config['pubchannel']) + "\nApprover Role: " + str(config['role']) + "\nApprover Channel: " + str(config['channel']) )
    pass

bot.run(TOKEN)