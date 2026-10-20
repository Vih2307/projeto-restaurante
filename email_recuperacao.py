import os
import smtplib
import ssl
from email.message import EmailMessage


def enviar_codigo(email, codigo):
    servidor = os.getenv("SMTP_SERVIDOR", "")
    porta = int(os.getenv("SMTP_PORTA", "587"))
    remetente = os.getenv("SMTP_EMAIL", "")
    senha = os.getenv("SMTP_SENHA", "")

    if not servidor or not remetente or not senha:
        raise ValueError("Configure o e-mail no arquivo .env.")

    mensagem = EmailMessage()
    mensagem["Subject"] = "Recuperação de senha - Restaurante BKV"
    mensagem["From"] = remetente
    mensagem["To"] = email
    mensagem.set_content(
        f"Seu código para alterar a senha é: {codigo}\n"
        "O código vale por 10 minutos e pode ser utilizado uma vez.\n"
        "Se você não solicitou a alteração, ignore este e-mail."
    )

    with smtplib.SMTP(servidor, porta, timeout=15) as conexao:
        conexao.starttls(context=ssl.create_default_context())
        conexao.login(remetente, senha)
        conexao.send_message(mensagem)
