import sqlite3
import os
from discord.ext import commands
from helpers import getConfig
import Printer

#Class for potentially destructive commands.
class Admin(commands.Cog):
    isBlocked = False
    def __init__(self, bot, con: sqlite3.Connection, printManager: Printer): 
        self.bot = bot
        self.con = con
        self.printManager = printManager
        async def checkBlocked(ctx):
            if self.isBlocked:
                await ctx.channel.send("Commands are currently blocked. Resolve rename first.")
            return not self.isBlocked
        bot.add_check(checkBlocked)
        
    @commands.command(help = "Deletes a quote with a specific ID. Requires permissions role.")
    @commands.has_role(getConfig("Permissions Role"))
    async def deleteQuote(self, ctx, id):
        await ctx.channel.send("Deleting quote...")
        await self.printManager.idQuote(ctx, id)
        cur = self.con.cursor()
        cur.execute("SELECT * FROM quotes WHERE id = :id", {"id": id})
        output = cur.fetchone()
        if(output is None):
            return

        if(output[5]): #Deleting saved attachment.
            os.remove(getConfig("Attachments") + str(id) + "." + output[5])

        cur.execute("DELETE FROM quotes WHERE id = :id", {"id": id})
        self.con.commit()
        await ctx.message.add_reaction(getConfig('Emoji'))
        #id is primary key, this should never delete more than one quote.
    
    #restart the bot
    @commands.command(name ="restart", aliases = ["r"], help = "Restarts the bot.")
    @commands.has_role(getConfig("Permissions Role"))
    async def restart(self, ctx): #ctx passes an argument into the body. a "context" (ctx)
        #sends react to message as confirmation to restart
        await ctx.message.add_reaction(getConfig('Emoji'))
        self.con.close()
        await self.bot.close()
    
    @commands.command(name ="rename", help = "Renames a quote author. No effect on aliases.")
    @commands.has_role(getConfig("Permissions Role"))
    async def rename(self, ctx, originalName, newName): 
        self.isBlocked = True
        cur = self.con.cursor()
        #cur.execute("BEGIN TRANSACTION")
        cur.execute("UPDATE quotes SET quoteAuthor = :newName WHERE quoteAuthor = :originalName", {"originalName": originalName, "newName": newName})
        cur.execute("SELECT changes()")
        rowsChanged = cur.fetchone()[0]
        message = await ctx.channel.send("This will make changes to " + str(rowsChanged) + " rows.\n" + \
                          "React with " + getConfig("Emoji") + " to confirm this change.\n" + \
                          "React with " + getConfig("EmojiCancel") + " to cancel this change.")
        
        def confirm(reaction, user):
            return user == ctx.message.author and reaction.message == message \
        and (reaction.emoji == getConfig("Emoji") or reaction.emoji == getConfig("EmojiCancel"))
        
        try: 
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=confirm)
        except:
            await ctx.channel.send("No confirmation. Changes canceled.")
            self.con.rollback()
        else: 
            #print(reaction)
            #await ctx.channel.send(reaction)
            if reaction.emoji == getConfig("EmojiCancel"):
                await ctx.channel.send("Changes canceled.")
                self.con.rollback()
            elif reaction.emoji == getConfig("Emoji"):
                await ctx.channel.send("Changes confirmed.")
                self.con.commit()
        
        cur.close()
        self.isBlocked = False