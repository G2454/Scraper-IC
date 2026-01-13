# Scraper

O scraper desenvolvido faz raspagem de 3 portais de notícias (G1, InfoMoney e o RSS do BBC em português) 

## Installation

É necessário ter o Docker instalado na sua máquina. Se tiver, apenas rode os seguintes comandos:

Para fazer build

```bash
docker build -f docker/Dockerfile -t projeto-ic:latest .
```

Para executar o container
```bash
docker run --rm -it --name projeto-ic projeto-ic:latest
```

## Dados gerados

Os dados são salvos em um banco de dados SQLITE local.

Caso tenha interesse em ver como os dados estão dispostos, baixe o data.db e utilize sites como [este](https://sqliteviewer.app/) para visualizar as tabelas.