import os
import discord
from discord.ext import commands
import asyncio
import re
import random
import time
from collections import defaultdict
from dotenv import load_dotenv
from fuzzywuzzy import fuzz

# Carregar variáveis de ambiente
load_dotenv()

# Configuração inicial
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Necessário para verificar cargos

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# Variáveis configuráveis (carregadas do .env)
TOKEN = os.getenv('TOKEN')
CANAL_COMANDOS_ID = int(os.getenv('CANAL_COMANDOS_ID'))
CATEGORIA_CURSOS_ID = int(os.getenv('CATEGORIA_CURSOS_ID'))
CARGO_ADMIN_ID = os.getenv('CARGO_ADMIN_ID')

# Configurações adicionais
LIMITE_RESULTADOS = 5
SIMILARIDADE_MINIMA = 70
LIMITE_SOLICITACOES = 5
TEMPO_ESFRIAMENTO = 600

# Sistema anti-flood
solicitacoes_usuarios = defaultdict(list)

def verificar_flood(user_id):
    """Verifica se o usuário excedeu o limite de solicitações"""
    # Admins não têm restrições
    if CARGO_ADMIN_ID:
        return False

    agora = time.time()

    # Remove solicitações antigas (> 10 minutos)
    solicitacoes_usuarios[user_id] = [
        t for t in solicitacoes_usuarios[user_id]
        if agora - t <= TEMPO_ESFRIAMENTO
    ]

    # Conta solicitações recentes
    total_solicitacoes = len(solicitacoes_usuarios[user_id])

    # Adiciona a nova solicitação
    solicitacoes_usuarios[user_id].append(agora)

    return total_solicitacoes >= LIMITE_SOLICITACOES

def criar_embed_flood(user_id):
    """Cria um embed elegante para notificar sobre limite de flood"""
    agora = time.time()
    ultima_solicitacao = max(solicitacoes_usuarios[user_id])
    tempo_restante = int(TEMPO_ESFRIAMENTO - (agora - ultima_solicitacao))
    minutos, segundos = divmod(tempo_restante, 60)

    embed = discord.Embed(
        title="⚠️ Limite de Solicitações Atingido",
        description="Você fez muitas solicitações em um curto período de tempo.",
        color=0xFF5733
    )

    embed.add_field(
        name="Limite Atual",
        value=f"{LIMITE_SOLICITACOES} solicitações a cada 10 minutos",
        inline=False
    )

    embed.add_field(
        name="Tempo Restante",
        value=f"{minutos} minutos e {segundos} segundos",
        inline=False
    )

    embed.add_field(
        name="Dica",
        value="Por favor aguarde para fazer novas pesquisas ou refine seus termos de busca",
        inline=False
    )

    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/179/179429.png")
    embed.set_footer(text="Sistema Anti-Flood | Bot de Cursos")

    return embed

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user.name}')
    print(f'🔍 Canal de comandos: {CANAL_COMANDOS_ID}')
    print(f'📚 Categoria de cursos: {CATEGORIA_CURSOS_ID}')
    print(f'👑 Cargo Admin: {CARGO_ADMIN_ID or "Nenhum"}')
    print(f'🛡️ Sistema Anti-Flood: {LIMITE_SOLICITACOES} solicitações/10 min (exceto admins)')

def criar_embed_ajuda():
    """Cria um embed elegante para mostrar a ajuda"""
    embed = discord.Embed(
        title="🎓 Central de Ajuda - Bot de Cursos",
        description="Aqui estão todos os comandos disponíveis e como usar o bot para encontrar cursos no servidor",
        color=0x3498DB
    )

    embed.add_field(
        name="🔍 !curso [termo de busca]",
        value="Busca cursos relacionados ao termo especificado\n"
              "Exemplo: `!curso marketing digital`\n"
              "Exemplo: `!curso python`",
        inline=False
    )

    embed.add_field(
        name="ℹ️ !help",
        value="Mostra esta mensagem de ajuda com todos os comandos disponíveis",
        inline=False
    )

    embed.add_field(
        name="⏳ Limite de Solicitações",
        value=f"Usuários comuns podem fazer até {LIMITE_SOLICITACOES} buscas a cada 10 minutos\n"
              "Administradores têm acesso ilimitado",
        inline=False
    )

    embed.add_field(
        name="💡 Dicas de Busca",
        value="• Use palavras-chave relevantes\n"
              "• Tente termos mais específicos para resultados melhores\n"
              "• Verifique a ortografia se não encontrar resultados",
        inline=False
    )

    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1940/1940611.png")
    embed.set_footer(
        text="Para mais assistência, contate os administradores do servidor",
        icon_url="https://cdn-icons-png.flaticon.com/512/732/732247.png"
    )

    return embed

def criar_embed_resultado(termo_busca, resultados):
    """Cria um embed elegante para mostrar os resultados"""
    # Cores aleatórias para cada embed
    cores = [0x1ABC9C, 0x3498DB, 0x9B59B6, 0xE91E63, 0xF1C40F]
    cor = random.choice(cores)

    embed = discord.Embed(
        title=f"🔍 Resultados para: {termo_busca}",
        description=f"Foram encontrados {len(resultados)} cursos relacionados à sua busca",
        color=cor
    )

    # Adiciona resultados como campos
    for idx, (titulo, link, canal_nome, similaridade) in enumerate(resultados, 1):
        emoji = "⭐" if similaridade >= 85 else "🔹" if similaridade >= 75 else "🔸"
        valor_campo = (
            f"**Canal:** #{canal_nome}\n"
            f"**Relevância:** {emoji} {similaridade}%\n"
            f"[🔗 Acessar curso]({link})"
        )

        embed.add_field(
            name=f"{idx}. {titulo[:80]}{'...' if len(titulo) > 80 else ''}",
            value=valor_campo,
            inline=False
        )

    # Rodapé
    embed.set_footer(
        text="Para mais informações, clique nos links acima",
        icon_url="https://cdn-icons-png.flaticon.com/512/2232/2232688.png"
    )

    return embed

def usuario_eh_admin(member):
    """Verifica se o usuário tem cargo de administrador"""
    if not CARGO_ADMIN_ID:
        return False

    # Verifica se o usuário tem o cargo admin
    return any(role.id == int(CARGO_ADMIN_ID) for role in member.roles)

@bot.command(name='curso')
async def buscar_curso(ctx, *, termo_busca: str = None):
    """Busca cursos na categoria especificada"""
    # Verifica se o comando foi enviado no canal correto
    if ctx.channel.id != CANAL_COMANDOS_ID:
        return

    # Verifica limite de solicitações apenas para não-admins
    if not usuario_eh_admin(ctx.author):
        if verificar_flood(ctx.author.id):
            embed_flood = criar_embed_flood(ctx.author.id)
            await ctx.send(embed=embed_flood)
            return

    # Se o usuário não especificar o termo de busca
    if not termo_busca:
        embed_ajuda = discord.Embed(
            title="❌ Termo de busca não especificado",
            description="Você precisa informar o que deseja buscar!\n\n"
                        "**Exemplos:**\n"
                        "`!curso marketing digital`\n"
                        "`!curso python`\n"
                        "`!curso investimentos`",
            color=0xE74C3C
        )
        embed_ajuda.add_field(
            name="Precisa de ajuda?",
            value="Use `!help` para ver todos os comandos disponíveis",
            inline=False
        )
        embed_ajuda.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/564/564619.png")
        await ctx.send(embed=embed_ajuda)
        return

    # Obtém a categoria pelo ID
    categoria = bot.get_channel(CATEGORIA_CURSOS_ID)

    if not categoria or not isinstance(categoria, discord.CategoryChannel):
        await ctx.send(f"❌ Categoria de cursos não encontrada ou ID inválido!")
        return

    # Mensagem de espera elegante
    embed_espera = discord.Embed(
        title="🔍 Buscando cursos...",
        description=f"Procurando por: `{termo_busca}`\nPor favor aguarde, isso pode levar alguns segundos.",
        color=0xF1C40F
    )
    embed_espera.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4206/4206243.png")
    msg_espera = await ctx.send(embed=embed_espera)

    resultados = []
    termo_busca_lower = termo_busca.lower().strip()

    # Busca assíncrona nos canais da categoria
    for canal in categoria.channels:
        if isinstance(canal, discord.TextChannel):
            try:
                async for mensagem in canal.history(limit=300):
                    # Verifica se a mensagem parece ser um curso
                    if not mensagem.content.strip() or len(mensagem.content) < 20:
                        continue

                    # Verifica correspondência usando fuzzy matching
                    conteudo = mensagem.content.lower()

                    # Calcula similaridade
                    similaridade = fuzz.token_set_ratio(termo_busca_lower, conteudo)

                    # Verifica se é uma correspondência válida
                    if similaridade >= SIMILARIDADE_MINIMA:
                        link = f"https://discord.com/channels/{ctx.guild.id}/{canal.id}/{mensagem.id}"

                        # Tenta encontrar um título significativo
                        titulo = mensagem.content.split('\n')[0]
                        if len(titulo) > 100 or titulo.strip() == "":
                            titulo = f"Curso em #{canal.name}"

                        resultados.append((titulo, link, canal.name, similaridade))

            except discord.Forbidden:
                print(f"⚠️ Sem permissão para ler o canal: {canal.name}")
                continue
            except Exception as e:
                print(f"⚠️ Erro no canal {canal.name}: {str(e)}")

    # Remove mensagem de espera
    try:
        await msg_espera.delete()
    except:
        pass

    # Processa resultados
    if not resultados:
        embed_vazio = discord.Embed(
            title="❌ Nenhum curso encontrado",
            description=f"Não encontramos cursos relacionados a: `{termo_busca}`\n\nTente usar palavras-chave diferentes ou termos mais específicos.",
            color=0xE74C3C
        )
        embed_vazio.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/564/564619.png")
        embed_vazio.add_field(
            name="Dicas de busca",
            value="• Verifique a ortografia\n• Use termos mais gerais\n• Tente abreviações\n• Use `!help` para ver mais dicas",
            inline=False
        )
        await ctx.send(embed=embed_vazio)
        return

    # Ordena por similaridade (melhores resultados primeiro)
    resultados.sort(key=lambda x: x[3], reverse=True)

    # Limita os resultados
    resultados = resultados[:LIMITE_RESULTADOS]

    # Cria e envia o embed de resultados
    embed_resultado = criar_embed_resultado(termo_busca, resultados)
    await ctx.send(embed=embed_resultado)

@bot.command(name='help')
async def ajuda(ctx):
    """Mostra a mensagem de ajuda"""
    # Verifica se o comando foi enviado no canal correto
    if ctx.channel.id != CANAL_COMANDOS_ID:
        return

    embed = criar_embed_ajuda()
    await ctx.send(embed=embed)

# Inicia o bot
if __name__ == "__main__":
    print("="*50)
    print("🎓 BOT DE BUSCA DE CURSOS - INICIANDO")
    print("="*50)
    print(f"🔍 Buscando na categoria: {CATEGORIA_CURSOS_ID}")
    print(f"💬 Respondendo no canal: {CANAL_COMANDOS_ID}")
    print(f"🔎 Similaridade mínima: {SIMILARIDADE_MINIMA}%")
    print(f"👑 Cargo Admin: {CARGO_ADMIN_ID or 'Nenhum'}")
    print(f"🛡️ Limite de solicitações: {LIMITE_SOLICITACOES} por usuário comum a cada 10 minutos")
    print("="*50)
    
    bot.run(TOKEN)