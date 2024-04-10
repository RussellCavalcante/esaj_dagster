import os
from datetime import datetime, timedelta, timezone

from dagster import AssetsDefinition, Field, OpExecutionContext, asset

import pytz

from esaj_dagster.crawler import main 

from esaj_dagster.email_sender import enviar_email

# from copel.assets.miner_wo.crawler_file_service import CrawlerFileService
# from copel.enums import ResourcesEnum

# DEFAULT_SA_ENGINE_RESOURCE_KEY = ResourcesEnum.SQLALCHEMY_ENGINE_KEY.value
# DEFAULT_S3_RESOURCE_KEY = ResourcesEnum.CRAWLER_S3_CONNECTOR_KEY.value
DEFAULT_NAME_KEY = "asset_source_esaj_miner"
DEFAULT_DESCRIPTION_KEY = "crawler_copel_miner"
DEFAULT_WALKTHROUHG_PATH = "os_data"
DEFAULT_SOURCE_TAG_KEY = "crawler-copel"


def source_to_crawler_asset_factory(
    name: str = DEFAULT_NAME_KEY,
    description: str = DEFAULT_DESCRIPTION_KEY,
    source_tag: str = DEFAULT_SOURCE_TAG_KEY,
    # sa_engine_resource_key: str = DEFAULT_SA_ENGINE_RESOURCE_KEY,
    # s3_resource_key: str = DEFAULT_S3_RESOURCE_KEY,
    walkthrough_path: str = DEFAULT_WALKTHROUHG_PATH,
) -> AssetsDefinition:
    """Factory for a source mining job. Defines a job using the source
    interface tomine file source servers and log them to betreated in
    the variable.s3_file.

    Parameters
    ----------
    name : str
        Name of the job.
    description : str
        Job description.
    source_tag : str
        Tag for the source.
    source_resource_key : str, optional
        Key for the source, by default "source".
    sa_engine_resource_key : str, optional
        Key for SQLAlchemy engine resource, by default "engine".
    s3_resource_key : str, optional
        Key for S3 wrapper resource, by default "s3".
    walkthrough_path : str, optional
        Path for the walkthrough, by default ".".
    walkthrough_kwargs : dict[str, Any], optional
        Kwargs for the walkthrough, by default {}.
    upload_kwargs : dict[str, Any], optional
        Kwargs for the upload, by default {}.

    Returns
    -------
    AssetDefinition
        Source Mining Asset.
    """

    @asset(
        name=name,
        description=description,
        key_prefix=["OS"],
        config_schema={
            "year": Field(int, default_value=datetime.now().year),
            "park": Field(str, default_value="All"),
        },
        group_name="EsajMiner",
    )
    def source_file_service_asset(context: OpExecutionContext) -> None:
       
        context.log.info("Starting mining process")
        main()


        current_datetime = datetime.now()

        # Obtendo o objeto de fuso horário "America/Fortaleza"
        fortaleza_timezone = pytz.timezone("America/Fortaleza")

        # Convertendo a data e hora atual para o fuso horário "America/Fortaleza"
        current_datetime_fortaleza = current_datetime.astimezone(fortaleza_timezone)

        # Obtendo a data no fuso horário "America/Fortaleza"
        current_date = current_datetime_fortaleza.strftime("%d/%m/%Y")

        data_datetime = datetime.strptime(current_date, '%d/%m/%Y')

        # Subtraindo um dia
        dia_anterior = data_datetime - timedelta(days=1)

        # Extraindo apenas a parte da data
        dia_anterior_string = dia_anterior.date().strftime('%d/%m/%Y')


        data_encontrada = dia_anterior_string
        download_dir = os.path.join(os.getcwd(), "esaj_dagster", 'esaj_data')
        caminho_arquivo_csv = download_dir + f"\clientes_busca_{data_encontrada.replace('/', '_')}.csv"

        email_origem = 'files.esaj.miner@outlook.com'
        senha = '05280528Russell'
        email_destino = 'recalcule@outlook.com'
        # email_destino = 'russell.cavalcante.2882@gmail.com'
        assunto = 'Consulta processual esaj miner !'
        mensagem = f'Olá, segue em anexo csv processo para o dia {data_encontrada}.'
        anexo_nome = f"clientes_busca_{data_encontrada.replace('/', '_')}.csv"
        anexo_caminho = caminho_arquivo_csv
    
        enviar_email(email_origem, senha, email_destino, assunto, mensagem, anexo_nome, anexo_caminho)


        context.log.info(f"Realizado envio para email: {email_destino}")
        os_data_path = os.path.join(os.getcwd(), "esaj_dagster", "esaj_data")

        # for file in service.walkthrough(path=os_data_path):
        #     context.log.info(str(file))
        #     service.upload(file)

        if os.path.exists(os_data_path):
            # Liste todos os arquivos na os_data_path
            arquivos = os.listdir(os_data_path)

            # Itere sobre os arquivos e remova-os
            for arquivo in arquivos:
                caminho_completo = os.path.join(os_data_path, arquivo)

                # Verifique se é um arquivo antes de remover
                if os.path.isfile(caminho_completo):
                    os.remove(caminho_completo)

    return source_file_service_asset


assets = [source_to_crawler_asset_factory()]
