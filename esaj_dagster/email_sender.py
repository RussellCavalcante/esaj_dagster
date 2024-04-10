import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os


from datetime import datetime, timedelta, timezone
import datetime
import imaplib
import email
import pandas as pd
from email.header import decode_header
from email.utils import parsedate_to_datetime


# Configurações do servidor SMTP


def get_mfa_from_webemail():
    """
    Retrieve the MFA token from a web email account.
    
    Parameters:
        current_date: The current date to compare the email dates against. (datetime)

    Returns: 
        dict: A dictionary containing the status and data of the retrieval process.
        - If the retrieval is successful, the status is "Success" and the data includes the token. (dict)
        - If the retrieval fails because the email date is not greater than the current date, the status is "Retry" and the data includes the reason. (dict)
        - If an error occurs during the retrieval process, the status is "Error" and the data includes the error message. (dict)
    """
    # Load credentials
    # load_dotenv()
    username = "files.esaj.miner@gmail.com"
    password = "05280528Russell"
    imap_host = "gmail.com"
     
    try:
        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(username, password)
        
        # Select the inbox
        mail.select("inbox")

        print("Logou")
        input()

        # Search for emails
        status, messages = mail.search(None, 'ALL')
        messages = messages[0].split(b' ')

        # Check if there are messages
        if not messages or messages == [b'']:
            return {"status": "Retry", "data": {"reason": "No emails found"}}

        # Fetch the latest email
        latest_email_id = messages[-1]
        res, msg = mail.fetch(latest_email_id, "(RFC822)")

        # Mark all emails for deletion
        for email_id in messages:
            mail.store(email_id, '+FLAGS', '\\Deleted')

        # Expunge to permanently delete the marked emails
        mail.expunge()

        # Process the email
        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                date = parsedate_to_datetime(msg["Date"])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()

                # Remove seconds and microseconds from the current date because Date is trimed by the IMAP server
                current_date = current_date - timedelta(seconds=current_date.second, microseconds=current_date.microsecond) 
                
                # Compare dates, if the email date is greater than or equal the current date, return the token
                if date >= current_date:
                    return {"status": "Success", "data": {"token": subject.strip()}}
        
        return {"status": "Retry", "data": {"reason": "Email date is not greater than current date"}}
    except Exception as e:
        return {"status": "Error", "data": {"error_message": str(e)}}
    finally:
        mail.close()
        mail.logout()




def enviar_email(email_origem, senha, email_destino, assunto, mensagem, anexo_nome, anexo_caminho):
    # Configuração do servidor SMTP do Gmail
    smtp_server = 'smtp-mail.outlook.com'
    smtp_port = 587

    # Iniciando conexão com o servidor SMTP
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    
    # Fazendo login no email remetente
    server.login(email_origem, senha)


    # Criando o objeto MIMEMultipart
    msg = MIMEMultipart()

    # Configurando os campos do email
    msg['From'] = email_origem
    msg['To'] = email_destino
    msg['Subject'] = assunto

    # Adicionando o corpo da mensagem
    msg.attach(MIMEText(mensagem, 'plain'))

    # Adicionando o anexo
    with open(anexo_caminho, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {anexo_nome}",)
    msg.attach(part)

    # Enviando o email
    server.sendmail(email_origem, email_destino, msg.as_string())

    # Encerrando a conexão com o servidor SMTP
    server.quit()

# Exemplo de uso


# data_encontrada = "08/04/2024"
# download_dir = os.path.join(os.getcwd(), 'esaj_data')
# caminho_arquivo_csv = download_dir + f"\clientes_busca_{data_encontrada.replace('/', '_')}.csv"

# email_origem = 'files.esaj.miner@outlook.com'
# senha = '05280528Russell'
# email_destino = 'recalcule@outlook.com'
# assunto = 'Consulta processual esaj miner !'
# mensagem = f'Olá, segue em anexo csv processo para o dia {data_encontrada}.'
# anexo_nome = 'clientes_busca_08_04_2024.csv'
# anexo_caminho = caminho_arquivo_csv


# enviar_email(email_origem, senha, email_destino, assunto, mensagem, anexo_nome, anexo_caminho)
# sender_email(nome_arquivo_csv)

# get_mfa_from_webemail()