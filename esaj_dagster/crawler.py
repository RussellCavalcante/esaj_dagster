#%%
import os
import time
from datetime import datetime, timedelta, timezone
import logging
import argparse
import sys
import pytz
import re
import csv

import imaplib
import email
import pandas as pd
from email.header import decode_header
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains

# Defined time constants
SHORT_WAIT_TIME = 5
MEDIUM_WAIT_TIME = 10
LONG_WAIT_TIME = 15

# Defined URL constants
URL_FROM_ESAJ_BASE = "https://esaj.tjce.jus.br"
URL_FROM_ESAJ_SERVICE = f"{URL_FROM_ESAJ_BASE}/esaj/portal.do?servico=740000"
URL_FROM_ESAJ_CPOPG = f"https://esaj.tjce.jus.br/cpopg/open.do"

def get_mfa_from_webemail(current_date: datetime):
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
    load_dotenv()
    username = os.getenv('login_webmail')
    password = os.getenv('password_webmail')
    imap_host = os.getenv('imap_host_webmail')
     
    try:
        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(username, password)
        
        # Select the inbox
        mail.select("inbox")

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

def exponential_retry(operation, current_date: datetime, max_retries:int =5):
    """
    Executes the given operation with exponential retry logic.

    Parameters:
        operation (function): The function to be executed.
        current_date (datetime): The current date for the operation.
        max_retries (int, optional): The maximum number of retries (default is 5).

    Returns:
        dict: The response dictionary.

    """
    wait_time = SHORT_WAIT_TIME
    for i in range(max_retries):
        response = operation(current_date)

        if response["status"] == "Success":
            return response  # Return the entire response dictionary
        elif response["status"] == "Error":
            return response  # Return the response in case of error
        elif response["status"] == "Retry":
            logging.info(f"Retry #{i + 1} in {wait_time} seconds")
            time.sleep(wait_time)
            wait_time *= 2  # Exponential increase
        else:
            # Handle unexpected status
            logging.error("Unexpected status:", response["status"])
            break

    return {"status": "Failed", "data": {"reason": "Failed after retries"}}
    
def create_driver(download_dir: str):
    """
    Creates and returns a WebDriver object for Chrome.

    Parameters:
        download_dir (str): The path to the download directory.

    Returns:
        driver (WebDriver): The WebDriver object for Chrome.

    Raises:
        WebDriverException: If the ChromeDriver executable is not found.
    """
    
    # Set up Chrome options
    prefs = {
            "download.default_directory": download_dir, # Change default directory for given path
            "download.prompt_for_download": False, # To auto download the file
            "download.directory_upgrade": True, # To auto download the file
            "plugins.always_open_pdf_externally": True, # It's for downloading PDFs intead of opening them in Chrome
            "profile.default_content_setting_values.notifications": 2,  # Disable notifications
            "profile.default_content_setting_values.popups": 2  # Disable popups
        }
    chrome_options = ChromeOptions()
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--headless=new") # Run in headless mode
    # chrome_options.add_argument("--no-sandbox") 
    # chrome_options.add_argument('--disable-gpu') 
    # chrome_options.add_argument('--disable-dev-shm-usage') # To overcome limited resource problems in Docker container

    # Set up Chrome Service
    service = ChromeService(executable_path=ChromeDriverManager().install()) # Automatically downloads the correct version of ChromeDriver for the version of Chrome installed on your system.

    # Create driver
    driver = webdriver.Chrome(service=service,options=chrome_options)

    return driver

def handle_process_1_grau_page(driver):
    """
    Handle the username page.

    Parameters:
        driver: The driver object for interacting with the web page.

    """
    #Load credentials
    # load_dotenv()
    # username = os.getenv('login_weg')

    # Find login elements
    wait = WebDriverWait(driver, SHORT_WAIT_TIME)  
    
    process_elem = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, '/html/body/table[3]/tbody/tr/td[1]/ul/li[1]/a')
            ))
    process_elem.click()

    process_elem = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, '/html/body/table[3]/tbody/tr/td[1]/ul/li[1]/ul/li[1]/a')
            ))
    process_elem.click()

    


    # login_elem.send_keys(username)
    # login_elem.send_keys(Keys.RETURN)
    

def handle_cpf_inputs(driver, cpf_cnpj:str):
    """
    Handles the MFA page by finding the MFA elements, loading the MFA token, and filling the MFA token in the form.

    Parameters:
        driver: The driver object for interacting with the web page.
        current_date: The current date.

    Raises:
        Exception: If the MFA token retrieval is unsuccessful.

    """
    
    # principal case

        # cpf_input_element = wait.until(EC.visibility_of_element_located((By.NAME, 'cbPesquisa')))

        # cpf_input_element.click()
    element_found = False

    while not element_found:
    
        try:
            wait = WebDriverWait(driver, SHORT_WAIT_TIME)
            # Se o elemento não for encontrado, continue procurando
            cpf_input_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/form/section/div[1]/div/select/option[3]')))

            cpf_input_element.click()

            cpf_input_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/form/section/div[2]/div/div[3]/div[1]/input')))

            cpf_input_element.send_keys(cpf_cnpj)
            # cpf_input_element.send_keys("567.629.843-04")
            # cpf_input_element.send_keys("59.109.165/0001-49")
            cpf_input_element.send_keys(Keys.RETURN)
            element_found = True

            return True

            

        except TimeoutException:
            not_have_process = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[1]/table/tbody/tr[2]/td[2]/li')))
            element_found = True
            return False

   

    #Load mfa token
    # response = exponential_retry(get_mfa_from_webemail, current_date)

    # print(response)
    # input()

    # Handle response
    # if response["status"] == "Success":
    #     # Fill mfa token
    #     mfa.send_keys(response["data"]["token"])
    #     mfa.send_keys(Keys.RETURN)
    # else:
    #     raise Exception(response["data"])

def get_distribution_date_and_process_number(driver, cpf_cnpj, current_date, download_dir):
    """
    Retrieves a list of files names and file paths in the specified OS folder for a given year and month.

    Parameters:
        driver: The driver object for interacting with the web page.
        year (int): The year of the folder to retrieve files from.
        month (int): The month of the folder to retrieve files from.

    Returns:
        list: A list of tuples containing the file names (FileLeafRefs) and file paths (FileRefs).
    """
    # Create url for given year and mont

     # principal case
    element_found = False

    while not element_found:
        try:

            wait = WebDriverWait(driver, SHORT_WAIT_TIME)
    
            cpf_input_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/div/div[1]/a/span[1]')))

            cpf_input_element.click()


            cpf_input_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/div/div[2]/div/div[1]/div')))

            distribution_date = cpf_input_element.text

            data_datetime = datetime.strptime(current_date, '%d/%m/%Y')

            # Subtraindo um dia
            dia_anterior = data_datetime - timedelta(days=1)

            # Extraindo apenas a parte da data
            dia_anterior_string = dia_anterior.date().strftime('%d/%m/%Y')

            padrao = r'(\d{2}/\d{2}/\d{4})'

            # Encontrar correspondências usando o padrão regex
            correspondencias = re.search(padrao, distribution_date)

            # Verificar se há correspondências e extrair a data
            if correspondencias:
                data = correspondencias.group(1)
                print("Data encontrada:", data)
                # input()

                print("data ------>>>>",data, "dia_anterior_string", dia_anterior_string)

                if dia_anterior_string == data:
                # if "23/03/2024" == data:
                    print("Entrou no if")
                    # numero do processo, classe, assunto, Foro, requerente, requerido , cpf_cnpj, Distribuição

                    # cpf_input_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/div/div[1]/a/span[1]')))
                    # cpf_input_element.click()

                    number_process = wait.until(EC.visibility_of_element_located((By.ID, 'numeroProcesso')))
                    number_process_data = number_process.text

                    class_process = wait.until(EC.visibility_of_element_located((By.ID, 'classeProcesso')))
                    class_process_data = class_process.text

                    assuntoProcesso = wait.until(EC.visibility_of_element_located((By.ID, 'assuntoProcesso')))
                    assuntoProcesso_data = assuntoProcesso.text

                    foroProcesso = wait.until(EC.visibility_of_element_located((By.ID, 'foroProcesso')))
                    foroProcesso_data = foroProcesso.text

                    requerente = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/table[1]/tbody/tr[1]/td[2]')))
                    requerente_data = requerente.text
                    
                    requerido = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/table[1]/tbody/tr[2]/td[2]')))
                    requerido_data = requerido.text

                    print(cpf_cnpj)

                    distribution_date = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/div/div[2]/div/div[1]/div')))

                    distribution_data = distribution_date.text

                    padrao = r'(\d{2}/\d{2}/\d{4})'

                    # Encontrar correspondências usando o padrão regex
                    correspondencias = re.search(padrao, distribution_data)

                    # Verificar se há correspondências e extrair a data
                    if correspondencias:
                        distribution_data_correct = correspondencias.group(1)
                        print("Data encontrada:", distribution_data)

                    # Nome do arquivo CSV
                    nome_arquivo_csv = download_dir + f"\clientes_revisional_busca_{distribution_data_correct.replace('/', '_')}.csv"

                    print(nome_arquivo_csv)
                    # input()
                    # Linha de dados
                    linha_dados = [number_process_data, class_process_data, assuntoProcesso_data.replace('\n', ' '), foroProcesso_data.replace('\n', ' '), requerente_data.replace('\n', ' '), requerido_data.replace('\n', ' '), cpf_cnpj, distribution_data_correct.replace('/', '_')]
                    
                    # Adicionando linha ao arquivo CSV
                    adicionar_linha_csv(nome_arquivo_csv, linha_dados)
                    # input()


                return False
            
            else:
                print("entrou no else")
                # input()
                return False

           

            

        except TimeoutException:
            print("entrou no time out")
            # input()
            return False
            
    

    # # Get variable g_listData that contains the list of files
    # g_listData = driver.execute_script("return g_listData;")

    # # Parse g_listData to get list of files
    # file_pairs = list(zip(
    #     [item['FileLeafRef'] for item in g_listData['ListData']['Row']],
    #     [item['FileRef'] for item in g_listData['ListData']['Row']]
    # ))

    # return file_pairs
        
def check_have_infos(driver):
    """
    Downloads a list of files from a given SharePoint web folder using a Selenium WebDriver.

    Parameters:
        driver: The driver object for interacting with the web page.
        list_of_files (list): A list of tuples containing the file names (FileLeafRefs) and file paths (FileRefs).

    """
    # Loop through the list of files and download them. Chrome is set to download PDF files instead of opening them
     # Create url for given year and mont

     # principal case
    element_found = False

    while not element_found:
        try:
            
            wait = WebDriverWait(driver, SHORT_WAIT_TIME)
            not_have_process = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[1]/table/tbody/tr[2]/td[2]/li')))
            
            element_found = True
            logging.info(f"Não existe processos !")
            return False

        except TimeoutException:            

            return True
    

# Função para adicionar uma linha ao arquivo CSV
def adicionar_linha_csv(nome_arquivo, linha):
    with open(nome_arquivo, 'a', newline='', encoding='utf-16') as arquivo_csv:
        escritor_csv = csv.writer(arquivo_csv)
        escritor_csv.writerow(linha)


def load_process_to_csv(driver, process_list, cpf_cnpj, download_dir):
    """
    Downloads a list of files from a given SharePoint web folder using a Selenium WebDriver.

    Parameters:
        driver: The driver object for interacting with the web page.
        list_of_files (list): A list of tuples containing the file names (FileLeafRefs) and file paths (FileRefs).

    """
    # Loop through the list of files and download them. Chrome is set to download PDF files instead of opening them
     # Create url for given year and mont

     # principal case

    try:
        
        # has_cabecalho = False        
        for process in process_list:
            
            driver.get(URL_FROM_ESAJ_CPOPG)
            wait = WebDriverWait(driver, MEDIUM_WAIT_TIME)

            # print(process)
            # input()
            

            process_select_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/form/section/div[1]/div/select/option[1]')))

            process_select_element.click()

            last_nuumber_process = re.findall(r'\.(\d+)$', process)

            resultado = re.search(r'\d+(?:-\d+)?\.\d+', process)

            if resultado:
                parte_ate_segundo_ponto = resultado.group()


            # print("last_nuumber_process --->>>",last_nuumber_process)

            # input()
            input_number_process = wait.until(EC.visibility_of_element_located((By.ID, 'numeroDigitoAnoUnificado')))

            input_number_process.send_keys(parte_ate_segundo_ponto)

            input_number_last_process = wait.until(EC.visibility_of_element_located((By.ID, 'foroNumeroUnificado')))

            input_number_last_process.send_keys(last_nuumber_process)
            
            # input_number_process.send_keys("03.017.677/0001-20")
            input_number_last_process.send_keys(Keys.RETURN)
                                                                                
            

            # numero do processo, classe, assunto, Foro, requerente, requerido , cpf_cnpj, Distribuição
            
            cpf_input_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/div/div[1]/a/span[1]')))
            cpf_input_element.click()

            number_process = wait.until(EC.visibility_of_element_located((By.ID, 'numeroProcesso')))
            number_process_data = number_process.text

            class_process = wait.until(EC.visibility_of_element_located((By.ID, 'classeProcesso')))
            class_process_data = class_process.text

            assuntoProcesso = wait.until(EC.visibility_of_element_located((By.ID, 'assuntoProcesso')))
            assuntoProcesso_data = assuntoProcesso.text

            foroProcesso = wait.until(EC.visibility_of_element_located((By.ID, 'foroProcesso')))
            foroProcesso_data = foroProcesso.text

            requerente = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/table[1]/tbody/tr[1]/td[2]')))
            requerente_data = requerente.text\
            
            requerido = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/table[1]/tbody/tr[2]/td[2]')))
            requerido_data = requerido.text

            distribution_date = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div[3]/div/div[2]/div/div[1]/div')))

            distribution_data = distribution_date.text

            padrao = r'(\d{2}/\d{2}/\d{4})'

            # Encontrar correspondências usando o padrão regex
            correspondencias = re.search(padrao, distribution_data)

            # Verificar se há correspondências e extrair a data
            if correspondencias:
                distribution_data_correct = correspondencias.group(1)
                print("Data encontrada:", distribution_data)

            # Nome do arquivo CSV
            nome_arquivo_csv = download_dir + f"\clientes_busca_{distribution_data_correct.replace('/', '_')}.csv"
            
             # Linha de dados
            linha_dados = [number_process_data, class_process_data, assuntoProcesso_data.replace('\n', ' '), foroProcesso_data.replace('\n', ' '), requerente_data.replace('\n', ' '), requerido_data.replace('\n', ' '), cpf_cnpj, distribution_data_correct.replace('/', '_')]
            
            # Adicionando linha ao arquivo CSV
            adicionar_linha_csv(nome_arquivo_csv, linha_dados)
            # input()

        return True

    except TimeoutException:
        return True

def check_have_more_process(driver, current_date):
    """
    Downloads a list of files from a given SharePoint web folder using a Selenium WebDriver.

    Parameters:
        driver: The driver object for interacting with the web page.
        list_of_files (list): A list of tuples containing the file names (FileLeafRefs) and file paths (FileRefs).

    """
    # Loop through the list of files and download them. Chrome is set to download PDF files instead of opening them
     # Create url for given year and mont

     # principal case
   

    try:
        process_list = []
        element_found = False
        while not element_found:

            last_process= ''
            # print("entrou no verificacao se existe mais processos para um forum")
            wait = WebDriverWait(driver, SHORT_WAIT_TIME)

            values_process = wait.until(EC.visibility_of_element_located((By.ID, 'listagemDeProcessos')))
                                                                                
            values_process_data = values_process.text

            # Convertendo a string em datetime
            data_datetime = datetime.strptime(current_date, '%d/%m/%Y')

            # Subtraindo um dia
            dia_anterior = data_datetime - timedelta(days=1)

            # Extraindo apenas a parte da data
            dia_anterior_string = dia_anterior.date().strftime('%d/%m/%Y')
            
            # print(dia_anterior_string)


            pattern = r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"

            # Encontrar todos os números de processo no texto
            process_numbers = re.findall(pattern, values_process_data)

            # Dividir o texto com base nos números de processo
            split_text = re.split(pattern, values_process_data)

            # Remover a primeira parte vazia
            split_text = split_text[1:]

            # Criar lista de informações para cada processo, combinando com o número do processo correspondente
            info_list = []
            for i, process_number in enumerate(process_numbers):
                info = process_number + '\n' + split_text[i].strip()  # Adicionar número de processo
                info_list.append(info)

            # Adicionar informações para o último processo
            info_list.append(process_numbers[-1] + '\n' + split_text[-1].strip())
            
            # Expressão regular para encontrar a data na lista de strings
            padrao_data = re.compile(r'\b\d{2}/\d{2}/\d{4}\b')

            # Itera sobre a lista de strings
            for texto in info_list:
                # Procura por todas as datas no texto
                datas_encontradas = padrao_data.findall(texto)
                # Verifica se a data procurada está presente
                # print("dia_anterior_string", dia_anterior_string, "----", datas_encontradas)
                if dia_anterior_string in datas_encontradas:
                # if "23/03/2024" in datas_encontradas:
                    # print(texto)
                    pattern = r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
                    # Encontra todas as correspondências ao padrão na string e coloca em uma lista
                    matches = re.findall(pattern, texto)
                    process_list.append(matches[0])


            number_process_per_page = wait.until(EC.visibility_of_element_located((By.ID, 'quantidadeProcessosNaPagina')))

            number_process_per_page_data = number_process_per_page.text

            indice_ate = number_process_per_page_data.index("até")

            last_process = number_process_per_page_data[indice_ate + len("até"):].strip()

            

            if int(last_process) == 25:
                next_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[1]/div[2]/ul/li[6]/a')))
                next_element.click()

            if int(last_process) > 25:
                next_element = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[1]/div[2]/ul/li[7]/a')))
                next_element.click()

            if int(last_process) < 25:
                    element_found = True

        
        if element_found and not process_list:
            print("saiu do while com o element found mas nao tem lista de processos")
            return False, process_list
        
        elif element_found and process_list:
            print("saiu do while com o element found e tem process_list")
            return True, process_list

    except TimeoutException:

        print("Numero de processos ->",process_list)
        if process_list:
            return True, process_list  # Retorna True e a lista de processos se houver processos
        else:
            return False, []  # Retorna False e uma lista vazia se não houver processos
    
   


def pipeline_crawler_esaj(download_dir:str, miner_path:str):
    """
    Pipeline for the crawler that downloads the files from a WEG SharePoint folder for a given year and month.

    Parameters:
        year (int): The year for which to process the files.
        month (int): The month for which to process the files.

    """
    # try:
        # Lista de arquivos na pasta
    arquivos = os.listdir(miner_path)

    has_cabecalho = False
    # Iterar sobre os arquivos
    for arquivo in arquivos:
        if arquivo.endswith('.xlsx'):  # Verificar se é um arquivo XLSX
            # Caminho completo do arquivo
            arquivo_path = os.path.join(miner_path, arquivo)
            
            # Carregar o arquivo XLSX
            df = pd.read_excel(arquivo_path, header=None, names=['Nome', 'CPF', 'Observacao'])
            
            # Iterar sobre as linhas do DataFrame
            for index, row in df.iterrows():
                # Verificar se a linha contém valores NaN
                if pd.isna(row['CPF']):
                    continue  # Pular para a próxima linha se não houver CPF
                    
                # Se o CPF for um número, podemos processar a linha
                
                # Aqui você pode fazer o que quiser com o CPF
                # por exemplo, validar ou armazenar em outra estrutura de dados
                
                # Verificar se há alguma observação
                # if pd.notna(row['Observacao']):
                #     print("Observacao:", row['Observacao'])

                cpf = str(row['CPF'])  # Converter para string
                print("Nome:", row['Nome'])
                print("CPF:", cpf)

                logging.info("Script started")
                # try:
                    # Create driver
                driver = create_driver(download_dir)

                # Get current date to avoid getting old MFA tokens
                # Obtendo o objeto de data e hora atual
                current_datetime = datetime.now()

                # Obtendo o objeto de fuso horário "America/Fortaleza"
                fortaleza_timezone = pytz.timezone("America/Fortaleza")

                # Convertendo a data e hora atual para o fuso horário "America/Fortaleza"
                current_datetime_fortaleza = current_datetime.astimezone(fortaleza_timezone)

                # Obtendo a data no fuso horário "America/Fortaleza"
                current_date = current_datetime_fortaleza.strftime("%d/%m/%Y")
                logging.info(f"Current date: {current_date}")

                # Navigate to SharePoint Weg URL
                driver.get(URL_FROM_ESAJ_SERVICE)
                
                # Handle login and MFA pages
                handle_process_1_grau_page(driver)
                # logging.info("Starting to fetch MFA token from email")

                if not handle_cpf_inputs(driver, cpf):
                    continue
                # logging.info("MFA token fetched successfully")   
                
                if not check_have_infos(driver):
                    continue
                
                print(current_date)
                
                # data_encontrada = "23/03/2024"
                # Nome do arquivo CSV
                
    
                boolean, process_list = check_have_more_process(driver, current_date)
                
                # Convertendo a string em datetime
                data_datetime = datetime.strptime(current_date, '%d/%m/%Y')

                # Subtraindo um dia
                dia_anterior = data_datetime - timedelta(days=1)

                # Extraindo apenas a parte da data
                dia_anterior_string = dia_anterior.date().strftime('%d/%m/%Y')

                # nome_arquivo_csv = download_dir + f"\clientes_busca_{data_encontrada.replace('/', '_')}.csv"

                nome_arquivo_csv = download_dir + f"\clientes_busca_{dia_anterior_string.replace('/', '_')}.csv"

                if not has_cabecalho:
                    cabecalho = ["numero_processo", "classe", "assunto", "foro", "requerente", "requerido", "cpf_cnpj", "distribuicao"]

                    # Adicionando cabeçalho ao arquivo CSV
                    adicionar_linha_csv(nome_arquivo_csv, cabecalho)
                    has_cabecalho = True

                if boolean and process_list:
                    if load_process_to_csv(driver, process_list, cpf, download_dir):
                        continue
                

                # Get a list of tuples containing the file names (FileLeafRefs) and file paths (FileRefs)

                if not get_distribution_date_and_process_number(driver, cpf, current_date, download_dir):
                    continue

                # Download Files
                logging.info("Starting downloading files")
                
                # logging.info("Files are downloaded successfully")

                        # Wait for download to complete
                time.sleep(SHORT_WAIT_TIME)

    # except Exception as e:
    #     logging.error(f"An error occurred while processing: {e}")

                # finally:
                #     driver.quit()
                #     logging.info("Script completed successfully")

def main():
    """
    Parse arguments and call the pipeline.
    """

    # Check environment variables
    # required_env_vars = ['login_webmail', 'password_webmail', 'imap_host_webmail']
    # for var in required_env_vars:
    #     if not os.getenv(var):
    #         logging.error(f"Environment variable {var} not set")
    #         sys.exit(1)


    # # Create an ArgumentParser object and add an argument for the year and month
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--year', type=int, help='The year for which to process the files.')
    # parser.add_argument('--month', type=int, help='The month for which to process the files.')
    # args = parser.parse_args()

    # Get the year and month values from the arguments
    # year = args.year
    # month = args.month

    # # Validate input arguments
    # if not 1 <= args.month <= 12:
    #     logging.error("Month must be between 1 and 12")
    #     sys.exit(1)

    # if args.year < 2000:  # Assuming year 2000 is the earliest year of interest
    #     logging.error("Year must be greater than 2000")
    #     sys.exit(1)

    # Set up download directory
    logging.basicConfig(level=logging.INFO)
    miner_path = os.path.join(os.getcwd(), "esaj_dagster","esaj_files")
    download_dir = os.path.join(os.getcwd(), "esaj_dagster","esaj_data")
    
    # Call the pipeline
    pipeline_crawler_esaj(download_dir, miner_path)

# logging.basicConfig(level=logging.INFO)
# main()


# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     main()
# %%
