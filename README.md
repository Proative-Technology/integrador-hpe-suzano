# Arquitetura da Solução

**Versão:** 1.0

---

# Índice

- [1. Objetivo](#1-objetivo)
- [2. Visão Geral da Arquitetura](#2-visão-geral-da-arquitetura)
- [3. Arquitetura Física](#3-arquitetura-física)
- [4. Fluxo de uma Requisição](#4-fluxo-de-uma-requisição)
- [5. Componentes da Solução](#5-componentes-da-solução)
- [6. Conceitos Fundamentais](#6-conceitos-fundamentais)
- [7. O Cluster Kubernetes](#7-o-cluster-kubernetes)
- [8. Os Nodes](#8-os-nodes)
- [9. O Deployment](#9-o-deployment)
- [10. O ReplicaSet](#10-o-replicaset)
- [11. Os Pods](#11-os-pods)
- [12. Por que utilizamos duas réplicas?](#12-por-que-utilizamos-duas-réplicas)
- [13. O Scheduler](#13-o-scheduler)
- [14. O Service](#14-o-service)
- [15. Ingress, NGINX Ingress Controller e AWS Network Load Balancer](#15-ingress-nginx-ingress-controller-e-aws-network-load-balancer)
- [16. ConfigMap e Secret](#16-configmap-e-secret)
- [17. Ciclo de Vida de uma Alteração](#17-ciclo-de-vida-de-uma-alteração)
- [18. Estratégia de Versionamento](#18-estratégia-de-versionamento)
- [19. Docker](#19-docker)
- [20. Amazon Elastic Container Registry (Amazon ECR)](#20-amazon-elastic-container-registry-amazon-ecr)
- [21. Anatomia de um Deployment Kubernetes](#21-anatomia-de-um-deployment-kubernetes)
- [22. Anatomia de um Service Kubernetes](#22-anatomia-de-um-service-kubernetes)
- [23. Anatomia de um Ingress Kubernetes](#23-anatomia-de-um-ingress-kubernetes)
- [24. NGINX Ingress Controller](#24-nginx-ingress-controller)
- [25. AWS Network Load Balancer (NLB)](#25-aws-network-load-balancer-nlb)
- [26. Amazon Elastic Kubernetes Service (Amazon EKS)](#26-amazon-elastic-kubernetes-service-amazon-eks)
- [27. Troubleshooting e Diagnóstico do Cluster Kubernetes](#27-troubleshooting-e-diagnóstico-do-cluster-kubernetes)
- [28. Runbook de Operação Diária da Plataforma](#28-runbook-de-operação-diária-da-plataforma)
- [29. Backup e Recuperação de Desastres (Backup & Disaster Recovery)](#29-backup-e-recuperação-de-desastres-backup--disaster-recovery)
- [30. Segurança da Plataforma](#30-segurança-da-plataforma)
- [31. Monitoramento e Observabilidade da Plataforma](#31-monitoramento-e-observabilidade-da-plataforma)
- [32. Evolução da Plataforma e Guia para Novos Integradores](#32-evolução-da-plataforma-e-guia-para-novos-integradores)

---

# 1. Objetivo

Este documento descreve detalhadamente a arquitetura utilizada pelo projeto **Integrador Topdesk**, implantado no Amazon Elastic Kubernetes Service (Amazon EKS).

Ao término desta leitura o desenvolvedor deverá compreender:

- por que a solução foi construída desta forma;
- como os componentes se relacionam;
- como uma requisição percorre toda a infraestrutura;
- como novas versões são implantadas;
- como ocorre a alta disponibilidade da aplicação;
- como diagnosticar problemas de infraestrutura.

Este documento não descreve apenas **como** executar procedimentos, mas principalmente **por que** cada componente foi escolhido.

---

# 2. Visão Geral da Arquitetura

A aplicação encontra-se implantada no Amazon EKS utilizando containers Docker armazenados no Amazon Elastic Container Registry (ECR).

Todo o código-fonte é mantido no GitHub.

O fluxo completo pode ser resumido da seguinte forma:

```text
                 GitHub
                    │
                    │ git pull / git push
                    ▼
        +----------------------------+
        | VM de Desenvolvimento      |
        | Ubuntu Linux               |
        | /opt/proative              |
        +----------------------------+
                    │
          docker build / testes
                    │
                    ▼
         Amazon Elastic Container Registry
                    │
             docker push
                    │
                    ▼
          Amazon Elastic Kubernetes Service
                    │
        Deployment (2 réplicas)
                    │
               ReplicaSet
            ┌────────┴────────┐
            │                 │
         Pod #1            Pod #2
            │                 │
            └────────┬────────┘
                     │
              ClusterIP Service
                     │
                Kubernetes Ingress
                     │
        NGINX Ingress Controller
                     │
       AWS Network Load Balancer
                     │
       api.proativetec.com.br
                     │
                 Cliente HTTP
```

Toda a infraestrutura foi projetada para que uma atualização da aplicação possa ser realizada sem indisponibilidade perceptível para o usuário.

---

# 3. Arquitetura Física

Atualmente o ambiente é composto pelos seguintes elementos.

## Desenvolvimento

Servidor Ubuntu Linux

Responsabilidades:

- desenvolvimento;
- testes;
- build das imagens Docker;
- publicação das imagens no Amazon ECR;
- administração do cluster EKS.

Diretório principal:

```text
/opt/proative
```

---

## GitHub

O GitHub é utilizado para armazenar todo o código-fonte da aplicação.

O repositório contém:

- código Python;
- Dockerfile;
- manifests Kubernetes;
- documentação;
- arquivos auxiliares.

O GitHub **não** armazena:

- senhas;
- Secrets;
- certificados privados;
- arquivos `.env` reais.

---

## Amazon Elastic Container Registry (ECR)

O Amazon ECR é o registro oficial de imagens Docker da aplicação.

Cada versão publicada recebe uma tag própria.

Exemplo:

```text
0.1.0
0.1.1
0.1.2
0.2.0
```

Nunca reutilizamos uma tag existente.

Essa prática garante:

- rastreabilidade;
- rollback simples;
- auditoria;
- repetibilidade.

---

## Amazon Elastic Kubernetes Service (EKS)

O Amazon EKS é responsável por executar a aplicação.

No ambiente atual temos:

- Cluster Kubernetes
- Namespace dedicado
- Deployment
- ReplicaSet
- Pods
- Service
- Ingress

O EKS é responsável por:

- iniciar containers;
- reiniciar containers com falha;
- distribuir Pods entre os Nodes;
- executar Rolling Updates;
- executar Rollbacks.

---

# 4. Fluxo de uma Requisição

A figura abaixo mostra exatamente o caminho percorrido por uma requisição HTTP.

```text
Cliente

    │

    ▼

api.proativetec.com.br

    │

    ▼

AWS Network Load Balancer

    │

    ▼

NGINX Ingress Controller

    │

    ▼

Ingress (/topdesk)

    │

    ▼

Service integrador-topdesk

    │

    ▼

Pod 1
ou
Pod 2

    │

    ▼

Flask / Gunicorn

    │

    ▼

MariaDB

    │

    ▼

Resposta HTTP
```

Observe que o cliente **nunca** acessa um Pod diretamente.

O cliente conhece apenas o domínio público.

Todo o restante da infraestrutura permanece oculto.

---

# 5. Componentes da Solução

A arquitetura é composta pelos seguintes componentes.

| Camada | Responsabilidade |
|---------|------------------|
| GitHub | Versionamento |
| Docker | Empacotamento da aplicação |
| Amazon ECR | Armazenamento das imagens |
| Amazon EKS | Orquestração |
| Deployment | Gerenciamento da aplicação |
| ReplicaSet | Quantidade de Pods |
| Pod | Execução do container |
| Service | Balanceamento interno |
| Ingress | Roteamento HTTP |
| NGINX Ingress Controller | Implementação do Ingress |
| AWS NLB | Balanceamento externo |
| Registro.br | Resolução DNS |

Cada um desses componentes será explicado detalhadamente nas próximas seções.

---

# 6. Conceitos Fundamentais

Antes de estudarmos Kubernetes é importante entender uma diferença fundamental.

Existe uma tendência de pensar:

```text
Servidor

↓

Aplicação
```

No Kubernetes essa visão não existe.

A arquitetura correta é:

```text
Cluster

↓

Node

↓

Pod

↓

Container

↓

Aplicação
```

Ou seja, a aplicação nunca "pertence" a um servidor específico.

Ela pertence ao Cluster.

Isso permite:

- alta disponibilidade;
- escalabilidade;
- atualização sem parada;
- recuperação automática de falhas.

---

# 7. O Cluster Kubernetes

O Kubernetes não administra servidores individuais.

Ele administra um **Cluster**.

Um Cluster é um conjunto de máquinas que trabalham como se fossem um único computador lógico.

No ambiente da Proative, o Cluster encontra-se hospedado no Amazon Elastic Kubernetes Service (Amazon EKS).

Sua principal responsabilidade é garantir que a aplicação esteja sempre disponível.

Em vez de pensar:

```text
Meu programa roda no servidor X
```

o pensamento correto é:

```text
Meu programa roda no Cluster
```

O Cluster decide automaticamente:

- em qual máquina executar um Pod;
- quando criar novos Pods;
- quando remover Pods;
- quando reiniciar Pods;
- quando mover Pods entre Nodes.

Essa abstração elimina a dependência de um servidor específico.

---

# 8. Os Nodes

Um Cluster é composto por um ou mais Nodes.

Cada Node é uma máquina virtual (ou física) capaz de executar Pods.

Atualmente o ambiente possui dois Worker Nodes.

```text
Amazon EKS Cluster

        │

 ┌──────┴─────────┐

 ▼                ▼

Node A        Node B

```

Cada Node possui:

- Sistema Operacional
- Container Runtime
- kubelet
- kube-proxy

e recursos como:

- CPU
- Memória
- Disco
- Rede

Os Nodes não conhecem a aplicação.

Eles apenas oferecem recursos para que o Kubernetes execute Pods.

---

## Por que utilizar mais de um Node?

Imagine que exista apenas um servidor.

```text
Cluster

    │

    ▼

Node A

    │

    ▼

Pod
```

Se o Node falhar:

- energia;
- hardware;
- kernel panic;
- manutenção;

a aplicação ficará indisponível.

Agora considere dois Nodes.

```text
Cluster

     │

 ┌───┴────┐

 ▼        ▼

Node A  Node B

```

Caso um Node falhe, o Kubernetes poderá recriar os Pods no outro Node.

Essa é uma das principais razões para utilizar Kubernetes.

---

# 9. O Deployment

O Deployment é provavelmente o objeto mais importante do Kubernetes.

Ele representa o estado desejado da aplicação.

Por exemplo:

```yaml
apiVersion: apps/v1

kind: Deployment

spec:

  replicas: 2
```

Isso significa:

> Quero que sempre existam dois Pods executando esta aplicação.

Observe a palavra importante:

**quero**.

O Deployment não executa Pods.

Ele apenas informa ao Kubernetes qual é o estado desejado.

O Kubernetes fará todo o restante.

---

## Responsabilidades do Deployment

O Deployment é responsável por:

- criar ReplicaSets;
- atualizar ReplicaSets;
- executar Rolling Updates;
- executar Rollbacks;
- substituir versões antigas;
- manter o número desejado de Pods.

Em outras palavras:

O Deployment administra a aplicação.

---

# 10. O ReplicaSet

O ReplicaSet é criado automaticamente pelo Deployment.

Normalmente o administrador nunca cria ReplicaSets manualmente.

O fluxo é:

```text
Deployment

      │

      ▼

ReplicaSet

      │

      ▼

Pods
```

O ReplicaSet possui apenas uma responsabilidade:

Garantir que exista exatamente a quantidade de Pods especificada.

Se o Deployment informa:

```yaml
replicas: 2
```

o ReplicaSet fará de tudo para manter exatamente dois Pods.

---

## Exemplo

Estado desejado:

```text
Pod A

Pod B
```

Situação atual:

```text
Pod A

Pod B
```

Tudo certo.

Agora imagine que um Pod foi removido.

```text
Pod A

X Pod B
```

O ReplicaSet detectará imediatamente:

```text
Desejado: 2

Atual: 1
```

Então criará automaticamente um novo Pod.

```text
Pod A

Pod C
```

Observe que ele não recria necessariamente o Pod antigo.

Ele cria um novo Pod.

---

# 11. Os Pods

O Pod é a menor unidade executável do Kubernetes.

É importante entender que:

O Kubernetes **não executa containers diretamente**.

Ele executa Pods.

Dentro de um Pod existe um ou mais containers.

No Integrador Topdesk temos:

```text
Pod

    │

    ▼

Container

    │

    ▼

Gunicorn

    │

    ▼

Flask

    │

    ▼

internalintegrator.py
```

Portanto:

Aplicação

↓

Flask

↓

Gunicorn

↓

Container Docker

↓

Pod

---

## Características de um Pod

Cada Pod possui:

- endereço IP próprio;
- sistema de arquivos próprio;
- processos próprios;
- memória própria;
- logs próprios.

Exemplo:

```bash
kubectl get pods -o wide
```

Resultado:

```text
NAME                                IP

integrador-topdesk-xxxx             10.50.62.25

integrador-topdesk-yyyy             10.50.92.230
```

Observe que cada Pod possui seu próprio IP.

Esses IPs mudam sempre que o Pod é recriado.

Por esse motivo nunca devemos acessar um Pod diretamente.

---

# 12. Por que utilizamos duas réplicas?

O Deployment foi configurado com:

```yaml
replicas: 2
```

Isso oferece diversas vantagens.

## Alta disponibilidade

Se um Pod falhar:

```text
Pod 1

Pod 2
```

↓

```text
Pod 1

X Pod 2
```

o ReplicaSet cria automaticamente:

```text
Pod 1

Pod 3
```

O usuário normalmente nem percebe essa troca.

---

## Atualização sem parada

Durante um Rolling Update:

```text
Pod antigo 1

Pod antigo 2
```

↓

```text
Pod novo

Pod antigo
```

↓

```text
Pod novo

Pod novo
```

Sempre existirá pelo menos um Pod atendendo requisições.

---

## Balanceamento

O Service distribui as requisições entre os dois Pods.

```text
Service

   │

 ┌─┴──────┐

 ▼        ▼

Pod A   Pod B
```

Nenhum cliente sabe qual Pod responderá.

Isso é transparente.

---

# 13. O Scheduler

Uma dúvida muito comum é:

> Quem decide em qual Node um Pod será executado?

A resposta é:

O Kubernetes Scheduler.

Quando um Pod precisa ser criado, o Scheduler analisa:

- CPU disponível;
- memória disponível;
- afinidade;
- taints;
- tolerations;
- restrições do Deployment.

Depois escolhe o Node mais adequado.

Exemplo:

```text
Cluster

        │

Scheduler

        │

 ┌──────┴──────┐

 ▼             ▼

Node A      Node B

```

No nosso ambiente atual, os Pods do Integrador Topdesk estão distribuídos entre os dois Worker Nodes.

Isso aumenta significativamente a disponibilidade da aplicação.

---

# 14. O Service

Até agora aprendemos que:

```
Cluster
   │
Deployment
   │
ReplicaSet
   │
Pods
```

Surge então uma pergunta importante.

> Como uma requisição chega até um Pod?

A resposta é:

**Ela nunca chega diretamente ao Pod.**

Ela chega primeiro ao **Service**.

---

# O problema dos Pods

Imagine que temos dois Pods.

```
Pod A

IP = 10.50.62.25
```

```
Pod B

IP = 10.50.92.230
```

Tudo parece perfeito.

Entretanto, existe um problema muito sério.

Os Pods são **efêmeros**.

Ou seja, eles podem desaparecer a qualquer momento.

Por exemplo:

```
Pod A

IP = 10.50.62.25
```

↓

Pod reiniciado

↓

```
Novo Pod

IP = 10.50.101.18
```

Observe que o endereço IP mudou.

Se um cliente estivesse acessando diretamente:

```
10.50.62.25
```

ele deixaria de funcionar imediatamente.

É exatamente por isso que **nunca acessamos Pods diretamente**.

---

# O Service resolve esse problema

O Service possui um endereço IP fixo dentro do Cluster.

Exemplo:

```bash
kubectl get svc -n integrador-topdesk
```

Resultado semelhante ao ambiente atual:

```
NAME                    TYPE        CLUSTER-IP

integrador-topdesk      ClusterIP   172.20.229.38
```

Observe:

O Service possui um IP.

Esse IP não muda quando os Pods são recriados.

Logo:

```
Cliente

↓

Service

↓

Pod
```

e nunca:

```
Cliente

↓

Pod
```

---

# Tipos de Service

O Kubernetes possui diversos tipos de Service.

Os principais são:

| Tipo | Utilização |
|--------|------------|
| ClusterIP | Comunicação interna |
| NodePort | Exposição através dos Nodes |
| LoadBalancer | Integração com provedores Cloud |
| ExternalName | Alias DNS |

No Integrador Topdesk utilizamos:

```
ClusterIP
```

porque quem expõe a aplicação para a Internet é o Ingress.

---

# Como o Service encontra os Pods?

Essa é uma das perguntas mais importantes de Kubernetes.

A resposta é:

**Labels.**

Observe o Deployment.

```
labels:

    app: integrador-topdesk
```

Os Pods herdam essa Label.

```
Pod A

app=integrador-topdesk
```

```
Pod B

app=integrador-topdesk
```

Agora veja o Service.

```
selector:

    app: integrador-topdesk
```

Observe que o Service não conhece Pods.

Ele conhece apenas Labels.

Em outras palavras:

```
Service

↓

Todos os Pods

↓

app=integrador-topdesk
```

Todos os Pods que possuírem essa Label passam automaticamente a fazer parte do balanceamento.

---

# O EndpointSlice

Quando você executou:

```bash
kubectl get endpointslice \
-n integrador-topdesk
```

obteve algo semelhante a:

```
NAME

integrador-topdesk-vw7gq

PORT

8889

ENDPOINTS

10.50.92.230

10.50.62.25
```

Muitas pessoas acreditam que o Service armazena essa lista.

Na realidade não.

Quem faz isso é o EndpointSlice.

O fluxo correto é:

```
Deployment

↓

Pods

↓

Labels

↓

Service

↓

EndpointSlice
```

---

# O que existe dentro do EndpointSlice?

Basicamente:

```
Service

↓

Lista de Pods

↓

IP

Porta

Estado
```

Por exemplo:

```
10.50.62.25:8889

Ready
```

```
10.50.92.230:8889

Ready
```

Essa lista é atualizada automaticamente.

---

# O que acontece quando um Pod morre?

Imagine:

```
Pod A

10.50.62.25
```

```
Pod B

10.50.92.230
```

EndpointSlice:

```
10.50.62.25

10.50.92.230
```

Agora o Pod A falha.

```
Pod A

X
```

O EndpointSlice passa a ser:

```
10.50.92.230
```

Poucos segundos depois o ReplicaSet cria um novo Pod.

```
Pod C

10.50.101.18
```

Automaticamente:

```
EndpointSlice

↓

10.50.92.230

10.50.101.18
```

Nenhum administrador precisou alterar nada.

---

# O kube-proxy

Outra pergunta importante.

Quem faz o balanceamento?

Muitas pessoas respondem:

"O Service."

Na realidade isso não é totalmente correto.

Quem faz o balanceamento é o **kube-proxy**.

O fluxo é:

```
Cliente

↓

ClusterIP

↓

kube-proxy

↓

EndpointSlice

↓

Pod
```

O kube-proxy utiliza as informações do EndpointSlice para decidir qual Pod receberá a requisição.

---

# Balanceamento

Suponha duas requisições consecutivas.

```
Request 1

↓

Service

↓

Pod A
```

```
Request 2

↓

Service

↓

Pod B
```

Ou:

```
Request 3

↓

Service

↓

Pod A
```

Isso ocorre automaticamente.

A aplicação Flask não sabe que existe balanceamento.

O Gunicorn também não.

Quem faz isso é a infraestrutura Kubernetes.

---

# O Service do Integrador Topdesk

No ambiente atual utilizamos:

```
Service

↓

ClusterIP

↓

Porta 80
```

Essa porta é convertida para:

```
TargetPort

↓

8889
```

Ou seja:

```
Cliente interno

↓

80

↓

Service

↓

8889

↓

Gunicorn

↓

Flask
```

---

# Vantagens do Service

O Service oferece diversas vantagens.

- IP fixo
- Descoberta automática dos Pods
- Balanceamento interno
- Independência dos Pods
- Alta disponibilidade
- Integração com o Ingress

Sem o Service, cada cliente teria que conhecer o IP de cada Pod.

Isso seria inviável.

---

# 15. Ingress, NGINX Ingress Controller e AWS Network Load Balancer

Até este ponto aprendemos que uma requisição chega ao Service.

Mas surge uma nova pergunta.

> Como uma requisição vinda da Internet chega ao Service?

A resposta envolve quatro componentes:

- DNS (Registro.br)
- AWS Network Load Balancer (NLB)
- NGINX Ingress Controller
- Kubernetes Ingress

Esses componentes trabalham em conjunto para permitir que um usuário acesse:

```
https://api.proativetec.com.br/topdesk
```

sem conhecer absolutamente nada sobre Kubernetes.

---

# Visão Geral

O caminho completo de uma requisição é:

```
Internet

    │

    ▼

Registro.br

    │

    ▼

AWS Network Load Balancer

    │

    ▼

NGINX Ingress Controller

    │

    ▼

Ingress

    │

    ▼

Service

    │

    ▼

Pod

    │

    ▼

Gunicorn

    │

    ▼

Flask
```

Observe que o usuário nunca sabe:

- qual Node recebeu a conexão;
- qual Pod respondeu;
- quantos Pods existem;
- se ocorreu um Rolling Update.

Toda essa complexidade fica escondida.

---

# O Registro.br

O Registro.br é responsável apenas pela resolução do nome.

No nosso ambiente existe um registro semelhante a:

```
api.proativetec.com.br

↓

CNAME

↓

k8s-ingressn-ingressn-2f4d5d3114-6d62b5d9a52120e3.elb.us-east-1.amazonaws.com
```

Observe que o Registro.br não conhece Kubernetes.

Ele apenas conhece um nome DNS.

---

# O DNS do NLB

O nome

```
k8s-ingressn-ingressn-2f4d5d3114-6d62b5d9a52120e3.elb.us-east-1.amazonaws.com
```

pertence ao AWS Network Load Balancer.

Quando o cliente resolve esse nome, obtém um dos endereços IP públicos do NLB.

Exemplo:

```
52.x.x.x
```

ou

```
3.x.x.x
```

Esses IPs podem mudar.

Por esse motivo apontamos o Registro.br para o **nome DNS** do NLB e nunca para um endereço IP.

---

# AWS Network Load Balancer

O AWS Network Load Balancer é o primeiro componente AWS que recebe a conexão TCP proveniente da Internet.

Ele possui duas responsabilidades principais:

- disponibilizar um endereço público;
- distribuir conexões para os Nodes do cluster.

Visualmente:

```
Internet

      │

      ▼

AWS NLB

      │

 ┌────┴────┐

 ▼         ▼

Node A   Node B
```

O NLB não conhece:

- Pods;
- Services;
- Ingress.

Ele conhece apenas os Nodes do cluster.

---

# Como o NLB foi criado?

No nosso ambiente ele foi criado automaticamente pelo Kubernetes.

Quando executamos:

```bash
kubectl get svc -n ingress-nginx
```

obtivemos:

```text
ingress-nginx-controller

TYPE

LoadBalancer
```

Observe o tipo:

```
LoadBalancer
```

Sempre que um Service desse tipo é criado em um ambiente AWS, o Kubernetes solicita automaticamente à AWS a criação de um Load Balancer.

Foi exatamente assim que surgiu:

```
k8s-ingressn-ingressn-2f4d5d3114-6d62b5d9a52120e3
```

---

# O Service LoadBalancer

É importante entender a diferença entre:

```
Service ClusterIP
```

e

```
Service LoadBalancer
```

No Integrador Topdesk utilizamos dois Services diferentes.

## Service do Integrador

```
ClusterIP
```

Responsabilidade:

Levar a requisição até os Pods.

---

## Service do NGINX

```
LoadBalancer
```

Responsabilidade:

Criar um AWS Network Load Balancer.

São dois Services completamente diferentes.

---

# NGINX Ingress Controller

Depois que o NLB entrega a conexão para um Node, ela chega ao NGINX Ingress Controller.

Ele é apenas uma aplicação executando dentro do Kubernetes.

No nosso ambiente:

```
Namespace

↓

ingress-nginx
```

Deployment:

```
ingress-nginx-controller
```

Ele recebe todas as conexões HTTP/HTTPS do cluster.

---

# O que o NGINX faz?

Ele analisa:

- Host HTTP

e

- Path HTTP

Exemplo:

```
Host

api.proativetec.com.br
```

Path

```
/topdesk
```

ou

```
/hpe-suzano
```

Com essas informações ele decide para qual aplicação encaminhar a requisição.

---

# O Kubernetes Ingress

O Ingress não recebe conexões.

Essa é uma dúvida muito comum.

O Ingress é apenas uma regra.

Por exemplo:

```yaml
host:

api.proativetec.com.br

path:

/topdesk

↓

service

integrador-topdesk
```

Outra regra:

```yaml
host:

api.proativetec.com.br

path:

/hpe-suzano

↓

service

integrador-hpe-suzano
```

Observe que o Ingress apenas descreve o roteamento.

Quem interpreta essas regras é o NGINX Ingress Controller.

---

# Fluxo do roteamento

Vamos acompanhar uma requisição.

```
https://api.proativetec.com.br/topdesk/api/v1.0/tasks
```

Primeiro:

```
Registro.br

↓

NLB
```

Depois:

```
NLB

↓

NGINX
```

O NGINX verifica:

```
Host

api.proativetec.com.br
```

Depois:

```
Path

/topdesk
```

Consulta as regras do Ingress.

Encontra:

```
/topdesk

↓

Service integrador-topdesk
```

Depois:

```
Service

↓

EndpointSlice

↓

Pod
```

Finalmente:

```
Gunicorn

↓

Flask

↓

internalintegrator.py
```

---

# Dois Integradores

Atualmente temos duas aplicações.

```
api.proativetec.com.br

                │

     ┌──────────┴──────────┐

     ▼                     ▼

 /topdesk            /hpe-suzano
```

Cada uma possui:

- Deployment próprio;
- Pods próprios;
- Service próprio.

Mas ambas utilizam:

- o mesmo NLB;
- o mesmo NGINX;
- o mesmo domínio.

Isso reduz custos e simplifica a administração.

---

# Por que não criar um Load Balancer para cada aplicação?

Seria possível.

```
Topdesk

↓

NLB próprio
```

```
HPE

↓

NLB próprio
```

Entretanto isso aumentaria:

- custo;
- quantidade de IPs;
- administração.

Por esse motivo utilizamos um único NLB.

O NGINX faz a separação através dos Paths.

---

# Certificados HTTPS

O certificado TLS também é utilizado pelo NGINX.

Quando o cliente estabelece a conexão HTTPS:

```
Cliente

↓

NLB

↓

NGINX
```

o certificado é apresentado.

No nosso ambiente utilizamos:

```
*.proativetec.com.br
```

Dessa forma:

```
api.proativetec.com.br
```

é atendido automaticamente.

---

# O caminho completo

A figura abaixo resume todo o fluxo.

```
Cliente

↓

Registro.br

↓

AWS DNS

↓

Network Load Balancer

↓

Node Kubernetes

↓

NGINX Ingress Controller

↓

Ingress

↓

Service

↓

EndpointSlice

↓

Pod

↓

Gunicorn

↓

Flask

↓

internalintegrator.py

↓

MariaDB
```

Observe que nenhum componente conhece todos os demais.

Cada componente possui apenas uma responsabilidade.

Essa separação torna a arquitetura extremamente modular.

---

# Benefícios dessa arquitetura

A solução oferece diversas vantagens.

- alta disponibilidade;
- escalabilidade;
- atualização sem parada;
- reutilização do mesmo domínio;
- reutilização do mesmo NLB;
- isolamento entre aplicações;
- facilidade para adicionar novos integradores.

Para criar um novo integrador normalmente basta criar:

- Deployment;
- Service;
- Ingress.

Sem alterar o restante da infraestrutura.

---

# 16. ConfigMap e Secret

---

# Objetivo

Uma aplicação moderna precisa de configurações.

Algumas dessas configurações podem ser públicas.

Outras são extremamente sensíveis.

O Kubernetes resolve esse problema utilizando dois objetos diferentes:

- ConfigMap
- Secret

A escolha correta entre eles é fundamental para a segurança da aplicação.

---

# O problema

Imagine que a aplicação precise das seguintes informações.

```
DB_HOST

DB_PORT

DB_NAME

DB_USER

DB_PASSWORD

TOPDESK_BASE_URL

API_BASIC_USER

API_BASIC_PASSWORD
```

Uma alternativa seria escrever tudo dentro do código Python.

Por exemplo:

```python
DB_PASSWORD="senha123"
```

Essa abordagem apresenta diversos problemas.

- alteração exige recompilar a imagem;
- a senha fica armazenada no GitHub;
- qualquer desenvolvedor pode visualizar a senha;
- não existe separação entre aplicação e configuração.

Essa abordagem nunca deve ser utilizada.

---

# Separando código e configuração

Uma boa prática é dividir o projeto em duas partes.

```
Código

↓

Imagem Docker
```

e

```
Configuração

↓

Kubernetes
```

Assim, uma alteração de configuração não exige alteração do código.

---

# ConfigMap

O ConfigMap armazena informações **não confidenciais**.

Exemplos:

```
LOG_LEVEL

DEBUG

ROOT_PATH

APP_NAME

TOPDESK_BASE_URL

DB_HOST

DB_PORT

DB_NAME

ATTACHES_PATH
```

Observe que nenhuma dessas informações representa risco caso alguém as visualize.

---

# O ConfigMap do Integrador Topdesk

No nosso ambiente o ConfigMap contém informações semelhantes às abaixo.

```
APP_NAME

ROOT_PATH

DEBUG

LOG_FILE

TOPDESK_BASE_URL

DB_HOST

DB_PORT

DB_NAME

DB_USER

ATTACHES_PATH
```

Essas configurações podem ser alteradas independentemente da imagem Docker.

---

# Como o ConfigMap é criado?

Normalmente utilizamos um manifesto YAML.

Exemplo simplificado:

```yaml
apiVersion: v1

kind: ConfigMap

metadata:

  name: integrador-topdesk-config

data:

  APP_NAME: Integrador Topdesk

  ROOT_PATH: /topdesk

  DB_HOST: mariadb.mariadb.svc.cluster.local

  DB_PORT: "3306"
```

Depois:

```bash
kubectl apply -f configmap.yaml
```

---

# Como o Pod utiliza o ConfigMap?

O Deployment referencia o ConfigMap.

```
Deployment

↓

ConfigMap

↓

Variáveis de ambiente

↓

Container
```

Exemplo:

```yaml
envFrom:

- configMapRef:

    name: integrador-topdesk-config
```

Quando o Pod inicia, todas essas variáveis passam a existir no ambiente Linux.

Podemos verificar:

```bash
kubectl exec \
-n integrador-topdesk \
deployment/integrador-topdesk \
-- env
```

---

# Alterando um ConfigMap

Suponha que desejamos alterar:

```
LOG_LEVEL
```

Basta modificar:

```
configmap.yaml
```

Depois:

```bash
kubectl apply -f configmap.yaml
```

Entretanto existe um detalhe muito importante.

---

# O ConfigMap atualiza o Pod automaticamente?

Não.

Essa é uma dúvida muito comum.

O ConfigMap é atualizado.

Entretanto o processo Python continua utilizando as variáveis carregadas durante o início do container.

Por esse motivo executamos:

```bash
kubectl rollout restart deployment integrador-topdesk \
-n integrador-topdesk
```

Assim novos Pods serão criados utilizando a nova configuração.

---

# Secret

O Secret possui exatamente a mesma finalidade do ConfigMap.

A diferença é:

Ele armazena informações confidenciais.

Exemplos.

```
DB_PASSWORD

API_BASIC_PASSWORD

API_TOKEN

ACCESS_KEY

SECRET_KEY
```

Essas informações nunca devem ser colocadas em um ConfigMap.

---

# O Secret do Integrador Topdesk

Atualmente utilizamos variáveis como:

```
DB_PASSWORD

API_BASIC_USER

API_BASIC_PASSWORD
```

Observe que o usuário pode ser considerado público.

Mesmo assim optamos por armazenar ambos no Secret para simplificar a administração.

---

# Como o Secret é criado?

Normalmente utilizamos um arquivo.

```
secret.env
```

Exemplo.

```
DB_PASSWORD=xxxxxxxx

API_BASIC_USER=opmonadmin

API_BASIC_PASSWORD=xxxxxxxx
```

Depois:

```bash
kubectl create secret generic integrador-topdesk-secret \
--namespace integrador-topdesk \
--from-env-file=secret.env
```

Ou:

```bash
kubectl apply -f secret.yaml
```

---

# O Secret é criptografado?

Existe um mito muito comum.

Muitas pessoas acreditam que o Secret é criptografado.

Na realidade ele é armazenado em Base64.

Por exemplo:

```
password

↓

cGFzc3dvcmQ=
```

Base64 não é criptografia.

Qualquer pessoa com acesso ao cluster pode executar:

```bash
kubectl get secret ...
```

e depois:

```bash
base64 -d
```

Por esse motivo o acesso ao cluster deve ser rigidamente controlado.

---

# Como o Pod recebe o Secret?

O fluxo é semelhante ao ConfigMap.

```
Secret

↓

Deployment

↓

Variáveis de ambiente

↓

Container
```

Exemplo.

```yaml
envFrom:

- secretRef:

    name: integrador-topdesk-secret
```

---

# Verificando as variáveis

Durante nossos testes utilizamos:

```bash
kubectl exec \
-n integrador-topdesk \
deployment/integrador-topdesk \
-- env
```

Também verificamos apenas algumas variáveis.

```bash
env | grep DB_
```

ou

```bash
env | grep API_
```

---

# Alterando um Secret

O procedimento recomendado é.

Atualizar:

```
secret.env
```

Depois:

```bash
kubectl create secret generic integrador-topdesk-secret \
--from-env-file=secret.env \
--dry-run=client \
-o yaml |
kubectl apply -f -
```

Em seguida:

```bash
kubectl rollout restart deployment integrador-topdesk \
-n integrador-topdesk
```

---

# GitHub

Nunca devemos enviar ao GitHub.

```
secret.env
```

O correto é manter apenas.

```
secret.env.example
```

Exemplo.

```
DB_PASSWORD=

API_BASIC_USER=

API_BASIC_PASSWORD=
```

Cada ambiente cria seu próprio:

```
secret.env
```

---

# ConfigMap x Secret

| ConfigMap | Secret |
|------------|--------|
| Configurações públicas | Informações confidenciais |
| Pode ser armazenado no GitHub | Nunca armazenar no GitHub |
| Não contém senhas | Contém senhas |
| Atualizado via apply | Atualizado via apply |
| Requer restart dos Pods | Requer restart dos Pods |

---

# Boas práticas

✔ Nunca colocar senhas no código Python.

✔ Nunca colocar senhas no Dockerfile.

✔ Nunca colocar senhas no GitHub.

✔ Nunca commitar arquivos `.env`.

✔ Versionar apenas `secret.env.example`.

✔ Utilizar ConfigMap apenas para configurações públicas.

✔ Utilizar Secret para qualquer informação confidencial.

✔ Após alteração de ConfigMap ou Secret executar Rolling Restart do Deployment.

---

# 17. Ciclo de Vida de uma Alteração

---

# Objetivo

Este capítulo descreve o procedimento completo para realizar uma alteração no código-fonte da aplicação, desde a modificação de um arquivo Python até sua disponibilização em produção no Amazon EKS.

Ao final deste processo teremos:

- código versionado no GitHub;
- nova imagem Docker publicada no Amazon ECR;
- nova versão implantada no Kubernetes;
- documentação sincronizada;
- possibilidade de rollback imediato.

Todo o processo deve ser executado a partir do servidor Linux de desenvolvimento.

---

# Visão Geral

O fluxo completo é representado pelo diagrama abaixo.

```text
                 GitHub
                    ▲
                    │
              git push
                    ▲
                    │
              git commit
                    ▲
                    │
        Testes de funcionamento
                    ▲
                    │
         Rolling Update (EKS)
                    ▲
                    │
             kubectl apply
                    ▲
                    │
      Atualização deployment.yaml
                    ▲
                    │
             docker push
                    ▲
                    │
              docker tag
                    ▲
                    │
             docker build
                    ▲
                    │
      Validação do código Python
                    ▲
                    │
        Alteração do código-fonte
```

---

# Passo 1 – Atualizar o repositório local

Antes de qualquer alteração, sincronize a árvore local.

```bash
cd /opt/proative/integrador-topdesk

git switch main

git pull --ff-only origin main
```

Verifique:

```bash
git status
```

Resultado esperado:

```text
On branch main

nothing to commit, working tree clean
```

Nunca inicie um desenvolvimento sobre uma árvore desatualizada.

---

# Passo 2 – Criar uma Branch

Cada alteração deve ser realizada em uma branch própria.

Exemplo:

```bash
git switch -c fix/correcao-acesso-mariadb
```

ou

```bash
git switch -c feature/anexos-topdesk
```

Evite trabalhar diretamente na branch `main`.

---

# Passo 3 – Alterar o código

Arquivo principal:

```text
app/bin/internalintegrator.py
```

Exemplo:

```bash
nano app/bin/internalintegrator.py
```

Após concluir a alteração:

```bash
git diff
```

Revise cuidadosamente todas as modificações antes de prosseguir.

---

# Passo 4 – Validar a sintaxe

Antes de construir uma nova imagem Docker, verifique se não existem erros de sintaxe.

Arquivo individual:

```bash
python3 -m py_compile \
app/bin/internalintegrator.py
```

Projeto completo:

```bash
python3 -m compileall app
```

A ausência de mensagens indica que a sintaxe está correta.

---

# Passo 5 – Atualizar a versão

Verifique a versão atualmente implantada.

```bash
kubectl get deployment integrador-topdesk \
-n integrador-topdesk \
-o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Exemplo:

```text
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.3
```

Defina a próxima versão.

```bash
export APP_VERSION=0.1.4
```

Nunca reutilize uma tag existente.

---

# Passo 6 – Construir a imagem Docker

A partir da raiz do projeto:

```bash
sudo docker build \
-t integrador-topdesk:${APP_VERSION} .
```

Confirme:

```bash
sudo docker image ls | grep integrador-topdesk
```

---

# Passo 7 – Autenticar no Amazon ECR

```bash
aws ecr get-login-password \
--profile proative \
--region us-east-1 |
sudo docker login \
--username AWS \
--password-stdin \
029142736054.dkr.ecr.us-east-1.amazonaws.com
```

Resultado esperado:

```text
Login Succeeded
```

---

# Passo 8 – Criar a Tag do ECR

```bash
sudo docker tag \
integrador-topdesk:${APP_VERSION} \
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:${APP_VERSION}
```

---

# Passo 9 – Publicar a imagem

```bash
sudo docker push \
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:${APP_VERSION}
```

Aguarde a conclusão do upload.

---

# Passo 10 – Atualizar o Deployment

Edite:

```text
deployment.yaml
```

Altere:

```yaml
image:

029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

Caso tenha havido alteração de escala, confirme:

```yaml
replicas: 2
```

---

# Passo 11 – Aplicar no Kubernetes

```bash
kubectl apply -f deployment.yaml
```

O Kubernetes iniciará automaticamente um Rolling Update.

---

# Passo 12 – Acompanhar o Rollout

```bash
kubectl rollout status \
deployment/integrador-topdesk \
-n integrador-topdesk
```

Resultado esperado:

```text
deployment "integrador-topdesk" successfully rolled out
```

---

# Passo 13 – Verificar os Pods

```bash
kubectl get pods \
-n integrador-topdesk \
-o wide
```

Confirme:

- dois Pods;
- STATUS Running;
- READY 1/1.

---

# Passo 14 – Testar internamente

```bash
kubectl run curl-test \
--rm -it \
--restart=Never \
--image=curlimages/curl \
-n integrador-topdesk \
-- curl \
http://integrador-topdesk/health
```

Resultado esperado:

```text
OK
```

---

# Passo 15 – Testar externamente

Enquanto o DNS do Registro.br ainda não estiver apontando para o novo NLB:

```bash
curl \
--resolve api.proativetec.com.br:443:<IP_DO_NLB> \
https://api.proativetec.com.br/topdesk/health
```

Após a alteração do DNS:

```bash
curl \
https://api.proativetec.com.br/topdesk/health
```

Resultado esperado:

```text
OK
```

---

# Passo 16 – Verificar os Logs

```bash
kubectl logs \
-l app=integrador-topdesk \
-n integrador-topdesk \
--tail=100
```

Confirme que não existem exceções.

---

# Passo 17 – Commit

```bash
git add .

git commit \
-m "Corrige acesso ao banco durante consulta de tickets"
```

Utilize mensagens descritivas.

---

# Passo 18 – Publicar no GitHub

```bash
git push \
-u origin \
fix/correcao-acesso-mariadb
```

Após aprovação:

```bash
git switch main

git pull --ff-only origin main
```

---

# Passo 19 – Criar uma Tag Git

Opcionalmente:

```bash
git tag -a v0.1.4 \
-m "Versão 0.1.4"
```

Depois:

```bash
git push origin v0.1.4
```

A convenção adotada é:

| Git | Docker |
|------|---------|
| v0.1.4 | 0.1.4 |

---

# Fluxograma Completo

```text
git pull
    │
Criar branch
    │
Editar internalintegrator.py
    │
py_compile
    │
compileall
    │
docker build
    │
docker tag
    │
docker push
    │
Editar deployment.yaml
    │
kubectl apply
    │
Rolling Update
    │
Verificar Pods
    │
Executar testes
    │
Analisar logs
    │
git commit
    │
git push
    │
Merge
    │
Tag Git
```

---

# Checklist

Antes de concluir uma alteração confirme:

- [ ] Repositório sincronizado
- [ ] Branch criada
- [ ] Código revisado
- [ ] Sintaxe validada
- [ ] Nova versão definida
- [ ] Build Docker concluído
- [ ] Imagem publicada no ECR
- [ ] Deployment atualizado
- [ ] Rollout concluído
- [ ] Dois Pods Running
- [ ] Testes executados
- [ ] Logs verificados
- [ ] Commit realizado
- [ ] Push realizado
- [ ] Documentação atualizada

---

# Considerações Finais

Seguindo este procedimento, todas as alterações tornam-se:

- rastreáveis;
- reproduzíveis;
- reversíveis através de rollback;
- documentadas;
- consistentes entre GitHub, ECR e Amazon EKS.

Este processo deve ser utilizado para qualquer evolução do Integrador Topdesk e servirá de modelo para os demais integradores da plataforma.


---

# 18. Estratégia de Versionamento

**Versão:** 1.0

---

# Objetivo

Este documento define a estratégia oficial de versionamento utilizada nos projetos da Proative executados em Kubernetes.

Os objetivos são:

- manter rastreabilidade completa;
- facilitar rollback;
- simplificar auditorias;
- padronizar os repositórios Git;
- sincronizar GitHub, Docker, Amazon ECR e Amazon EKS.

---

# Conceitos

Durante o ciclo de vida de uma aplicação existirão quatro versões diferentes.

```
Código

↓

Commit Git

↓

Tag Git

↓

Imagem Docker

↓

Deployment Kubernetes
```

Todas elas devem estar sincronizadas.

---

# Exemplo Completo

```
Git Commit

↓

9ab34ef
```

↓

```
Git Tag

↓

v0.1.4
```

↓

```
Docker

↓

integrador-topdesk:0.1.4
```

↓

```
Amazon ECR

↓

0.1.4
```

↓

```
Deployment

↓

image:

integrador-topdesk:0.1.4
```

Observe que a versão é sempre a mesma.

---

# Semantic Versioning

Adotaremos o padrão SemVer.

```
MAJOR.MINOR.PATCH
```

Exemplo:

```
1.0.0
```

---

## PATCH

Incrementado quando ocorre:

- correção de bugs;
- ajustes pequenos;
- melhorias internas.

Exemplo.

```
0.1.3

↓

0.1.4
```

---

## MINOR

Incrementado quando existe nova funcionalidade.

Exemplo.

```
0.1.4

↓

0.2.0
```

---

## MAJOR

Incrementado quando ocorre quebra de compatibilidade.

Exemplo.

```
0.9.0

↓

1.0.0
```

---

# Convenção das Branches

As Branches devem seguir o padrão abaixo.

## main

Contém apenas versões estáveis.

Nunca desenvolver diretamente.

---

## feature

Novas funcionalidades.

Exemplo.

```
feature/upload-anexos
```

---

## fix

Correções.

Exemplo.

```
fix/mariadb-connection
```

---

## hotfix

Correções urgentes em produção.

Exemplo.

```
hotfix/token-expiration
```

---

## release

Preparação para uma versão.

Exemplo.

```
release/0.2.0
```

---

# Fluxo de Desenvolvimento

```
main

 │

 ├───────────────┐

 ▼               ▼

feature      fix

 │               │

 └──────┬────────┘

        ▼

     Pull Request

        ▼

      main
```

---

# Convenção dos Commits

Utilizar mensagens objetivas.

Exemplos.

```
fix: corrige acesso ao MariaDB
```

```
feature: adiciona upload de anexos
```

```
docs: atualiza README
```

```
refactor: reorganiza camada de autenticação
```

```
test: adiciona testes unitários
```

Evite mensagens como:

```
ajustes
```

```
teste
```

```
corrigindo
```

Essas mensagens não ajudam em auditorias futuras.

---

# Versionamento das Imagens Docker

As imagens Docker devem utilizar exatamente a mesma versão da Tag Git.

Exemplo.

```
Git

v0.1.4
```

↓

```
Docker

0.1.4
```

Nunca utilizar:

```
latest
```

em produção.

---

# Versionamento no Amazon ECR

Cada Push cria uma nova versão.

Exemplo.

```
integrador-topdesk

↓

0.1.0

0.1.1

0.1.2

0.1.3

0.1.4
```

Nunca sobrescrever uma Tag existente.

---

# Versionamento do Deployment

O Deployment deve apontar para uma Tag específica.

Exemplo.

```yaml
image:

029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

Nunca utilizar:

```yaml
latest
```

---

# Como descobrir a versão em produção

Através do Kubernetes.

```bash
kubectl get deployment \
integrador-topdesk \
-n integrador-topdesk \
-o jsonpath='{.spec.template.spec.containers[0].image}'
```

Resultado.

```
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

---

# Como descobrir o Commit correspondente

Através da Tag Git.

```bash
git show v0.1.4
```

ou

```bash
git rev-list -n 1 v0.1.4
```

Assim conseguimos localizar exatamente o código que originou a imagem em produção.

---

# Releases

Cada versão estável deve possuir uma Release no GitHub.

Exemplo.

```
Release

v0.1.4
```

Descrição.

```
Correção da conexão com MariaDB.

Melhoria da autenticação Basic.

Correção da consulta de Tickets.
```

---

# Rollback

Como todas as versões permanecem armazenadas no ECR, um rollback é simples.

Editar:

```
deployment.yaml
```

Alterar:

```
0.1.4
```

↓

```
0.1.3
```

Aplicar.

```bash
kubectl apply -f deployment.yaml
```

O Kubernetes realizará automaticamente o Rolling Update para a versão anterior.

---

# Matriz de Versionamento

| Git | Docker | ECR | Produção |
|------|---------|-----|-----------|
| v0.1.3 | 0.1.3 | 0.1.3 | Sim |
| v0.1.4 | 0.1.4 | 0.1.4 | Testes |
| v0.2.0 | 0.2.0 | 0.2.0 | Desenvolvimento |

Essa tabela permite saber rapidamente qual versão está implantada.

---

# Boas Práticas

✔ Nunca utilizar `latest`.

✔ Nunca reutilizar Tags.

✔ Nunca alterar uma imagem já publicada.

✔ Sempre criar uma Tag Git para versões implantadas.

✔ Sempre manter Git, Docker e ECR sincronizados.

✔ Utilizar nomes de Branch padronizados.

✔ Utilizar mensagens de Commit descritivas.

✔ Criar Releases para versões estáveis.

---

# Resumo

A estratégia de versionamento adotada garante:

- rastreabilidade completa;
- facilidade de rollback;
- sincronização entre GitHub, Docker, Amazon ECR e Amazon EKS;
- histórico confiável de alterações;
- padronização dos projetos da Proative.

Essa política deve ser utilizada em todos os integradores da plataforma.

---

# 19. Docker

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve a utilização do Docker no projeto **Integrador Topdesk**.

Ao término da leitura o desenvolvedor deverá compreender:

- o que é Docker;
- por que utilizamos containers;
- como a imagem da aplicação é construída;
- como funciona o Dockerfile;
- como validar uma imagem localmente;
- como preparar uma imagem para publicação no Amazon ECR.

---

# O que é Docker?

Docker é uma plataforma de virtualização baseada em containers.

Diferentemente de uma máquina virtual tradicional, um container compartilha o Kernel do sistema operacional hospedeiro, tornando sua execução extremamente leve.

Enquanto uma máquina virtual contém:

- Sistema Operacional
- Kernel
- Bibliotecas
- Aplicação

um container contém apenas:

- Bibliotecas necessárias
- Aplicação

O Kernel é compartilhado.

---

# Máquina Virtual x Container

## Máquina Virtual

```
Hardware

↓

Hypervisor

↓

VM 1
    Sistema Operacional
    Aplicação

↓

VM 2
    Sistema Operacional
    Aplicação
```

Cada máquina virtual possui seu próprio sistema operacional.

---

## Container

```
Hardware

↓

Sistema Operacional

↓

Docker Engine

↓

Container 1

↓

Container 2

↓

Container 3
```

Todos compartilham o mesmo Kernel.

Isso reduz significativamente:

- consumo de memória;
- tempo de inicialização;
- utilização de disco.

---

# O Container do Integrador Topdesk

No nosso projeto cada Pod executa um único container.

```
Pod

↓

Container Docker

↓

Gunicorn

↓

Flask

↓

internalintegrator.py
```

O Kubernetes não executa diretamente o código Python.

Ele executa um container Docker.

---

# O Dockerfile

O Dockerfile descreve como construir uma imagem.

No Integrador Topdesk utilizamos um Dockerfile semelhante ao seguinte:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["gunicorn", "..."]
```

Cada instrução cria uma nova camada da imagem.

---

# O conceito de Camadas (Layers)

Uma imagem Docker é composta por diversas camadas.

```
Camada 5

CMD

↓

Camada 4

pip install

↓

Camada 3

COPY

↓

Camada 2

WORKDIR

↓

Camada 1

python:3.10-slim
```

Essas camadas permitem reutilização e reduzem o tempo de construção.

---

# Imagem x Container

Esses conceitos são frequentemente confundidos.

## Imagem

A imagem é um modelo.

Ela não executa nenhum processo.

Exemplo:

```
integrador-topdesk:0.1.4
```

---

## Container

O container é uma instância em execução da imagem.

```
Imagem

↓

Container
```

No Kubernetes, cada Pod cria automaticamente um container a partir da imagem especificada.

---

# Construindo a Imagem

Na raiz do projeto:

```bash
cd /opt/proative/integrador-topdesk
```

Construção:

```bash
docker build \
-t integrador-topdesk:0.1.4 .
```

O parâmetro `-t` define o nome e a versão da imagem.

---

# O que acontece durante o build?

Durante o `docker build` o Docker executa cada instrução do Dockerfile.

Fluxo simplificado:

```
FROM

↓

WORKDIR

↓

COPY

↓

RUN pip install

↓

CMD

↓

Imagem pronta
```

Caso uma etapa falhe, a construção é interrompida.

---

# Verificando a Imagem

Listar imagens locais:

```bash
docker image ls
```

Filtrar apenas o projeto:

```bash
docker image ls | grep integrador-topdesk
```

Resultado esperado:

```
REPOSITORY            TAG

integrador-topdesk    0.1.4
```

---

# Testando Localmente

Antes de enviar a imagem para o Amazon ECR é recomendável executá-la localmente.

Exemplo:

```bash
docker run \
--rm \
-p 8889:8889 \
integrador-topdesk:0.1.4
```

Depois, em outro terminal:

```bash
curl http://localhost:8889/health
```

Resultado esperado:

```
OK
```

---

# Logs do Container

Containers em execução:

```bash
docker ps
```

Visualizar logs:

```bash
docker logs <container_id>
```

Acompanhar em tempo real:

```bash
docker logs -f <container_id>
```

---

# Removendo Containers

Parar um container:

```bash
docker stop <container_id>
```

Remover:

```bash
docker rm <container_id>
```

---

# Removendo Imagens

Listar:

```bash
docker image ls
```

Remover:

```bash
docker rmi integrador-topdesk:0.1.4
```

Caso existam containers utilizando a imagem, será necessário removê-los primeiro.

---

# Boas Práticas

✔ Utilizar versões explícitas.

✔ Nunca utilizar `latest` em produção.

✔ Testar a imagem localmente antes do envio ao ECR.

✔ Manter o Dockerfile simples.

✔ Evitar instalar ferramentas desnecessárias na imagem.

✔ Utilizar imagens base oficiais.

✔ Reduzir o tamanho da imagem sempre que possível.

✔ Manter o `requirements.txt` atualizado.

---

# Troubleshooting

## Erro durante o build

Verifique:

- Dockerfile;
- requirements.txt;
- conectividade com a Internet.

---

## Erro ao iniciar o container

Execute:

```bash
docker logs <container_id>
```

---

## Porta em uso

Verifique:

```bash
ss -ltnp
```

ou

```bash
netstat -ltnp
```

---

# 20. Amazon Elastic Container Registry (Amazon ECR)

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve o funcionamento do Amazon Elastic Container Registry (Amazon ECR) e sua utilização no projeto Integrador Topdesk.

Ao final da leitura o desenvolvedor deverá compreender:

- O que é um Container Registry;
- O que é um Repository;
- O que é uma Image;
- O que é uma Tag;
- O que é um Digest;
- Como publicar imagens;
- Como listar imagens;
- Como o Kubernetes obtém uma imagem;
- Boas práticas de versionamento.

---

# O que é o Amazon ECR?

O Amazon Elastic Container Registry (Amazon ECR) é o serviço da AWS responsável pelo armazenamento de imagens Docker.

Ele funciona de forma semelhante ao Docker Hub, porém integrado ao ecossistema AWS.

No nosso ambiente utilizamos exclusivamente o Amazon ECR como repositório oficial das imagens dos integradores.

---

# Visão Geral

O fluxo é simples.

```
docker build

↓

Imagem Local

↓

docker push

↓

Amazon ECR

↓

Amazon EKS

↓

Pod
```

A imagem é construída apenas uma vez.

Depois disso, todos os Pods passam a utilizar exatamente a mesma imagem.

---

# Conceitos Fundamentais

Existem quatro conceitos que costumam ser confundidos.

```
Registry

↓

Repository

↓

Image

↓

Tag
```

Vamos entender cada um.

---

# Registry

O Registry é o serviço responsável por armazenar imagens.

No nosso ambiente o Registry é:

```
Amazon ECR
```

Ele pertence à conta AWS.

Exemplo:

```
029142736054
```

---

# Repository

Dentro do Registry existem diversos repositórios.

Exemplo.

```
integrador-topdesk

integrador-hpe-suzano

integrador-zabbix-opmon
```

Cada projeto possui seu próprio Repository.

---

# Image

Uma Image representa uma versão específica da aplicação.

Exemplo.

```
integrador-topdesk
```

Essa imagem pode possuir diversas versões.

---

# Tag

A Tag identifica uma versão da imagem.

Exemplo.

```
0.1.0

0.1.1

0.1.2

0.2.0
```

A Tag nunca deve ser reutilizada.

---

# Digest

Além da Tag existe o Digest.

Exemplo.

```
sha256:

ab47d3b...

```

Enquanto a Tag pode ser alterada, o Digest identifica de forma única uma imagem.

Mesmo que duas imagens possuam a mesma Tag, seus Digests serão diferentes.

---

# Estrutura do ECR

No nosso ambiente:

```
Conta AWS

↓

Amazon ECR

↓

Repository

↓

integrador-topdesk

↓

Tag

↓

0.1.4
```

---

# URI da Imagem

Cada imagem possui um endereço único.

Exemplo.

```
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

Essa URI é utilizada pelo Kubernetes.

---

# Autenticação

Antes de publicar uma imagem é necessário autenticar o Docker no ECR.

Utilizamos:

```bash
aws ecr get-login-password \
--profile proative \
--region us-east-1 |
docker login \
--username AWS \
--password-stdin \
029142736054.dkr.ecr.us-east-1.amazonaws.com
```

Resultado esperado:

```
Login Succeeded
```

Essa autenticação possui validade temporária.

---

# Construção da Imagem

A construção ocorre localmente.

```bash
docker build \
-t integrador-topdesk:0.1.4 .
```

Neste momento a imagem ainda existe apenas no computador local.

---

# Criando a Tag do ECR

Antes do envio criamos uma nova Tag.

```bash
docker tag \
integrador-topdesk:0.1.4 \
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

Observe que nenhuma cópia da imagem é criada.

Apenas um novo identificador.

---

# Publicando

Depois:

```bash
docker push \
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

Fluxo:

```
Imagem Local

↓

Upload

↓

Amazon ECR
```

---

# Como listar imagens

```bash
aws ecr describe-images \
--profile proative \
--region us-east-1 \
--repository-name integrador-topdesk
```

Podemos obter apenas as Tags.

```bash
aws ecr list-images \
--profile proative \
--region us-east-1 \
--repository-name integrador-topdesk
```

---

# Como o Kubernetes baixa a imagem?

Quando aplicamos:

```yaml
image:

029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

o Deployment informa ao Kubernetes:

```
Utilize esta imagem.
```

O Kubernetes verifica:

```
Node

↓

Container Runtime

↓

Amazon ECR

↓

Download
```

Caso a imagem ainda não exista no Node ela será baixada automaticamente.

---

# Cache

Se a imagem já estiver presente no Node, normalmente não será necessário novo download.

Isso acelera o Rolling Update.

---

# Atualizando uma versão

Quando alteramos:

```
0.1.3

↓

0.1.4
```

o Kubernetes identifica que a imagem mudou.

Isso inicia automaticamente um novo Rolling Update.

---

# Nunca utilizar "latest"

Embora o Docker permita:

```
latest
```

essa prática deve ser evitada.

Exemplo ruim.

```yaml
image:

integrador-topdesk:latest
```

Problemas.

- impossível saber a versão em produção;
- difícil realizar rollback;
- auditoria comprometida.

Sempre utilizar uma Tag explícita.

---

# Removendo imagens antigas

Listar imagens.

```bash
aws ecr list-images \
--repository-name integrador-topdesk
```

Excluir.

```bash
aws ecr batch-delete-image \
--repository-name integrador-topdesk \
--image-ids imageTag=0.0.9
```

Recomenda-se manter versões antigas para facilitar rollback.

---

# Política de Retenção

Uma boa política é manter:

- últimas 20 versões;
- todas as Releases oficiais.

Versões intermediárias podem ser removidas periodicamente.

---

# Segurança

Nunca compartilhar:

- URI privada do ECR com credenciais;
- Access Keys;
- Secret Keys.

O acesso ao ECR deve ocorrer através da AWS CLI utilizando um perfil autorizado.

---

# Custos

O Amazon ECR cobra por:

- armazenamento das imagens;
- transferência de dados quando aplicável.

Como as imagens do Integrador Topdesk possuem aproximadamente 200 MB, o custo é bastante reduzido.

---

# Fluxograma Completo

```
Docker Build

↓

Imagem Local

↓

Docker Tag

↓

Docker Login

↓

Docker Push

↓

Amazon ECR

↓

Deployment

↓

Kubernetes

↓

Node

↓

Container Runtime

↓

Download

↓

Pod

↓

Aplicação
```

---

# Boas Práticas

✔ Utilizar Tags semânticas.

✔ Nunca reutilizar Tags.

✔ Nunca utilizar latest.

✔ Manter histórico de versões.

✔ Publicar apenas imagens testadas.

✔ Sincronizar Tag Docker e Tag Git.

✔ Verificar a imagem implantada antes do deploy.

---

# 21. Anatomia de um Deployment Kubernetes

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve detalhadamente cada seção do arquivo `deployment.yaml` utilizado pelo projeto **Integrador Topdesk**.

Ao término da leitura o desenvolvedor será capaz de:

- entender cada campo do Deployment;
- alterar o número de réplicas;
- atualizar a imagem da aplicação;
- configurar variáveis de ambiente;
- compreender como o Kubernetes cria os Pods.

---

# O que é um Deployment?

O Deployment é um recurso do Kubernetes responsável por manter a aplicação no estado desejado.

Em outras palavras, o Deployment informa ao Kubernetes:

> "Quero que esta aplicação esteja sempre executando desta forma."

Exemplo simplificado:

```yaml
apiVersion: apps/v1
kind: Deployment
```

A partir desse momento, o Kubernetes assume toda a administração da aplicação.

---

# Estrutura Geral

Um Deployment é composto pelas seguintes partes.

```text
Deployment

├── apiVersion
├── kind
├── metadata
├── spec
│     ├── replicas
│     ├── selector
│     └── template
│            ├── metadata
│            └── spec
│                  ├── containers
│                  ├── volumes
│                  ├── env
│                  ├── probes
│                  └── restartPolicy
```

---

# apiVersion

Exemplo:

```yaml
apiVersion: apps/v1
```

Define a versão da API Kubernetes utilizada.

Para Deployments modernos sempre utilizamos:

```yaml
apps/v1
```

---

# kind

Exemplo:

```yaml
kind: Deployment
```

Indica ao Kubernetes qual objeto será criado.

Exemplos de outros tipos:

```text
Service
Ingress
ConfigMap
Secret
StatefulSet
DaemonSet
Job
CronJob
```

---

# metadata

Exemplo:

```yaml
metadata:

  name: integrador-topdesk

  namespace: integrador-topdesk
```

O bloco `metadata` identifica o objeto.

No nosso ambiente:

| Campo | Valor |
|--------|-------|
| name | integrador-topdesk |
| namespace | integrador-topdesk |

---

# namespace

O namespace funciona como uma divisão lógica dentro do Cluster.

```
Cluster

├── default

├── ingress-nginx

├── mariadb

├── integrador-topdesk

└── integrador-hpe-suzano
```

Cada aplicação possui seu próprio namespace.

Isso facilita:

- organização;
- segurança;
- administração.

---

# spec

Todo o comportamento do Deployment encontra-se dentro do bloco:

```yaml
spec:
```

É aqui que definimos:

- quantidade de Pods;
- imagem Docker;
- portas;
- ConfigMap;
- Secret;
- estratégias de atualização.

---

# replicas

Exemplo.

```yaml
replicas: 2
```

Esse campo informa:

```
Desejo dois Pods.
```

O ReplicaSet garantirá esse estado continuamente.

Se alterarmos para:

```yaml
replicas: 5
```

o Kubernetes criará cinco Pods.

---

# selector

Exemplo.

```yaml
selector:

  matchLabels:

    app: integrador-topdesk
```

O selector informa quais Pods pertencem ao Deployment.

Observe que ele utiliza Labels.

---

# Labels

Os Pods recebem automaticamente a Label.

```yaml
labels:

  app: integrador-topdesk
```

Essa mesma Label será utilizada posteriormente pelo Service.

Fluxo:

```
Deployment

↓

Label

↓

Service

↓

EndpointSlice
```

---

# template

O bloco template descreve como cada Pod será criado.

```yaml
template:
```

Tudo que estiver dentro desse bloco será replicado para todos os Pods.

---

# template.metadata

Exemplo.

```yaml
template:

  metadata:

    labels:

      app: integrador-topdesk
```

As Labels definidas aqui serão atribuídas a cada novo Pod.

---

# template.spec

Este bloco descreve o conteúdo do Pod.

```yaml
template:

  spec:
```

Aqui definimos:

- containers;
- volumes;
- restartPolicy;
- serviceAccount;
- imagePullSecrets;
- tolerations;
- affinity.

---

# containers

Exemplo.

```yaml
containers:

- name: integrador-topdesk
```

Uma lista de containers executados dentro do Pod.

No Integrador Topdesk utilizamos apenas um container.

---

# image

Exemplo.

```yaml
image:

029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.4
```

Este é um dos campos mais importantes.

Sempre que alteramos a Tag:

```
0.1.4

↓

0.1.5
```

o Kubernetes inicia automaticamente um Rolling Update.

---

# imagePullPolicy

Pode assumir três valores.

```
Always

IfNotPresent

Never
```

Recomendação.

```
IfNotPresent
```

ou

```
Always
```

dependendo da estratégia de versionamento.

Como utilizamos Tags explícitas, `IfNotPresent` costuma ser suficiente.

---

# ports

Exemplo.

```yaml
ports:

- containerPort: 8889
```

Essa é a porta utilizada pelo Gunicorn.

Observe que não é a porta do Service.

Temos:

```
Service

80
```

↓

```
Container

8889
```

---

# env

Variáveis individuais.

Exemplo.

```yaml
env:

- name: DEBUG

  value: "False"
```

No nosso ambiente preferimos utilizar ConfigMap e Secret.

---

# envFrom

Exemplo.

```yaml
envFrom:

- configMapRef:

    name: integrador-topdesk-config

- secretRef:

    name: integrador-topdesk-secret
```

Todas as variáveis são carregadas automaticamente.

Isso reduz significativamente o tamanho do Deployment.

---

# volumes

Volumes permitem persistência de dados.

Exemplo.

```yaml
volumes:

- name: logs
```

No Integrador Topdesk utilizamos volumes para:

- logs;
- anexos.

---

# volumeMounts

Relaciona um volume ao sistema de arquivos do container.

Exemplo.

```yaml
volumeMounts:

- mountPath: /app/logs

  name: logs
```

A aplicação passa a enxergar:

```
/app/logs
```

como um diretório persistente.

---

# restartPolicy

Normalmente:

```yaml
restartPolicy: Always
```

Caso o processo Python termine inesperadamente:

```
Gunicorn

↓

Erro

↓

Container encerra

↓

Kubernetes reinicia
```

O desenvolvedor não precisa intervir.

---

# livenessProbe

Verifica se a aplicação continua saudável.

Exemplo.

```yaml
livenessProbe:

  httpGet:

    path: /health
```

Caso a aplicação deixe de responder:

```
Kubernetes

↓

Reinicia o Pod
```

---

# readinessProbe

Verifica se o Pod já pode receber tráfego.

Enquanto a resposta for negativa:

```
Service

↓

não envia requisições
```

Isso evita indisponibilidade durante Rolling Updates.

---

# resources

Permite limitar consumo de CPU e memória.

Exemplo.

```yaml
resources:

  requests:

    cpu: 200m

    memory: 256Mi

  limits:

    cpu: 500m

    memory: 512Mi
```

Embora opcional, é altamente recomendado em produção.

---

# strategy

Define como ocorrerão atualizações.

Exemplo.

```yaml
strategy:

  type: RollingUpdate
```

O Kubernetes substitui Pods gradualmente.

Nunca remove todos ao mesmo tempo.

---

# Fluxo de Criação

Quando executamos:

```bash
kubectl apply -f deployment.yaml
```

ocorre:

```
Deployment

↓

ReplicaSet

↓

Scheduler

↓

Node

↓

Pod

↓

Container

↓

Gunicorn

↓

Flask

↓

Aplicação disponível
```

---

# Alterações mais comuns

Durante a manutenção normalmente alteramos apenas:

- imagem;
- número de réplicas;
- ConfigMap;
- Secret;
- recursos;
- probes.

Os demais campos raramente sofrem alterações.

---

# Boas Práticas

✔ Utilizar nomes consistentes.

✔ Manter Labels padronizadas.

✔ Utilizar ConfigMap para configurações.

✔ Utilizar Secret para senhas.

✔ Configurar probes.

✔ Definir limites de recursos.

✔ Nunca utilizar a Tag `latest`.

✔ Versionar o Deployment no GitHub.

---

# 22. Anatomia de um Service Kubernetes

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve detalhadamente o recurso **Service** utilizado pelo projeto Integrador Topdesk.

Ao final deste capítulo o desenvolvedor deverá compreender:

- por que um Service existe;
- por que nunca acessamos Pods diretamente;
- como funciona o ClusterIP;
- como ocorre o balanceamento interno;
- como o Service encontra os Pods;
- como o Service se integra ao Ingress.

---

# O problema

Imagine que existam dois Pods.

```
Pod A

IP = 10.50.62.25
```

```
Pod B

IP = 10.50.92.230
```

O cliente poderia acessar:

```
http://10.50.62.25:8889
```

Entretanto isso é uma péssima ideia.

Os Pods podem desaparecer a qualquer instante.

Exemplo.

```
Pod A

↓

Falha

↓

Novo Pod

↓

IP = 10.50.101.18
```

Todo cliente que conhecia:

```
10.50.62.25
```

pararia imediatamente de funcionar.

Era exatamente esse problema que o Kubernetes precisava resolver.

---

# O Service

O Service cria um endereço estável para representar um conjunto de Pods.

```
Service

↓

ClusterIP

↓

172.20.229.38
```

Os clientes passam a acessar o Service.

Nunca os Pods.

---

# Arquitetura

```
Cliente

↓

ClusterIP

↓

Service

↓

EndpointSlice

↓

Pod A

ou

Pod B
```

Observe que o cliente nunca conhece:

- Pod A

nem

- Pod B

Ele conhece apenas:

```
172.20.229.38
```

---

# Estrutura Geral

Um Service possui aproximadamente esta estrutura.

```yaml
apiVersion: v1

kind: Service

metadata:

spec:

  selector:

  ports:

  type:
```

---

# apiVersion

Sempre:

```yaml
apiVersion: v1
```

---

# kind

```yaml
kind: Service
```

Informa ao Kubernetes que será criado um recurso Service.

---

# metadata

Exemplo.

```yaml
metadata:

  name: integrador-topdesk

  namespace: integrador-topdesk
```

---

# type

O tipo define como o Service será exposto.

Os principais tipos são:

```
ClusterIP

NodePort

LoadBalancer

ExternalName
```

---

# ClusterIP

No Integrador Topdesk utilizamos:

```yaml
type: ClusterIP
```

O Kubernetes cria automaticamente um endereço IP interno.

Exemplo.

```
172.20.229.38
```

Esse endereço existe apenas dentro do Cluster.

Não pode ser acessado pela Internet.

---

# Por que ClusterIP?

Porque quem expõe a aplicação externamente é o Ingress.

Assim temos:

```
Internet

↓

Ingress

↓

ClusterIP

↓

Pods
```

Essa arquitetura reduz custos e simplifica o ambiente.

---

# selector

Exemplo.

```yaml
selector:

  app: integrador-topdesk
```

O selector informa quais Pods pertencem ao Service.

Ele utiliza Labels.

Fluxo:

```
Deployment

↓

Labels

↓

Service
```

---

# Labels

Os Pods recebem automaticamente:

```yaml
labels:

  app: integrador-topdesk
```

O Service procura exatamente essa Label.

Todos os Pods que possuírem essa Label passam a fazer parte do balanceamento.

---

# ports

No Integrador Topdesk utilizamos algo semelhante a:

```yaml
ports:

- port: 80

  targetPort: 8889
```

Observe que existem duas portas diferentes.

---

# port

```
80
```

É a porta do Service.

O Ingress conversa com essa porta.

---

# targetPort

```
8889
```

É a porta do container.

Mais especificamente:

```
Gunicorn
```

Fluxo:

```
Service

80

↓

Container

8889
```

---

# Fluxo completo

```
Cliente

↓

Ingress

↓

Service

80

↓

Pod

8889

↓

Gunicorn

↓

Flask
```

---

# O EndpointSlice

Quando o Service é criado, o Kubernetes cria automaticamente um EndpointSlice.

Exemplo.

```
kubectl get endpointslice
```

Resultado.

```
10.50.62.25

8889
```

```
10.50.92.230

8889
```

Essa lista é atualizada automaticamente.

---

# Balanceamento

Quando chegam diversas requisições.

```
Request 1

↓

Pod A
```

```
Request 2

↓

Pod B
```

```
Request 3

↓

Pod A
```

O balanceamento ocorre automaticamente.

Nenhuma alteração é necessária na aplicação.

---

# SessionAffinity

Por padrão.

```yaml
sessionAffinity: None
```

Cada requisição poderá ser enviada para qualquer Pod.

Caso necessário poderíamos utilizar:

```
ClientIP
```

fazendo com que um cliente permaneça sempre no mesmo Pod.

No Integrador Topdesk isso não é necessário.

---

# internalTrafficPolicy

No ambiente atual:

```yaml
internalTrafficPolicy: Cluster
```

Isso significa:

Qualquer Pod pode atender qualquer requisição.

Mesmo que esteja em outro Node.

---

# Relação com o Deployment

O Service não conhece Deployments.

Ele conhece apenas Labels.

Fluxo.

```
Deployment

↓

Pods

↓

Labels

↓

Service
```

---

# Relação com o Ingress

O Ingress também não conhece Pods.

Ele conhece apenas Services.

Fluxo.

```
Ingress

↓

Service

↓

Pods
```

---

# Relação com o EndpointSlice

O EndpointSlice mantém a lista de Pods disponíveis.

Fluxo.

```
Service

↓

EndpointSlice

↓

Lista de Pods
```

Sempre que um Pod entra ou sai do cluster, essa lista é atualizada automaticamente.

---

# Como uma requisição chega ao Gunicorn?

Vamos acompanhar uma requisição.

```
https://api.proativetec.com.br/topdesk/health
```

Primeiro.

```
Registro.br
```

↓

```
AWS NLB
```

↓

```
NGINX Ingress Controller
```

↓

```
Ingress
```

↓

```
Service

porta 80
```

↓

```
Pod

porta 8889
```

↓

```
Gunicorn
```

↓

```
Flask
```

↓

```
internalintegrator.py
```

Observe que a aplicação nunca sabe que existe um Service.

Quem realiza toda a tradução é o Kubernetes.

---

# Alterações comuns

Durante a manutenção normalmente alteramos apenas:

- selector
- port
- targetPort
- annotations

O ClusterIP normalmente nunca é alterado.

---

# Troubleshooting

## O Service existe mas não responde

Verifique:

```bash
kubectl get service \
-n integrador-topdesk
```

---

## O Service não possui Pods

Verifique:

```bash
kubectl get endpointslice \
-n integrador-topdesk
```

Se não existir nenhum Endpoint, normalmente existe problema nas Labels.

---

## O targetPort está incorreto

Verifique.

```
Service

↓

8889
```

deve coincidir com:

```
containerPort

8889
```

Caso contrário o tráfego não chegará ao Gunicorn.

---

# Boas Práticas

✔ Nunca acessar Pods diretamente.

✔ Sempre utilizar Labels consistentes.

✔ Manter selector e Deployment sincronizados.

✔ Utilizar ClusterIP para aplicações expostas por Ingress.

✔ Verificar EndpointSlice durante diagnósticos.

✔ Documentar todas as portas utilizadas.

---

# 23. Anatomia de um Ingress Kubernetes

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve detalhadamente o funcionamento do recurso **Ingress** utilizado pelo projeto Integrador Topdesk.

Ao final da leitura o desenvolvedor deverá compreender:

- o que é um Ingress;
- por que ele existe;
- como funciona o roteamento HTTP;
- como o Ingress se integra ao NGINX Ingress Controller;
- como múltiplas aplicações compartilham o mesmo domínio;
- como adicionar novos integradores sem criar novos Load Balancers.

---

# O problema

Até agora sabemos que existe um Service.

Por exemplo:

```
Service

↓

172.20.x.x
```

Entretanto surge uma pergunta.

Como um usuário da Internet acessa esse Service?

A resposta é:

**Ele não acessa.**

Quem faz essa ponte é o Ingress.

---

# Arquitetura

```
Internet

↓

AWS NLB

↓

NGINX Ingress Controller

↓

Ingress

↓

Service

↓

Pods
```

Observe que:

O Ingress nunca conversa diretamente com Pods.

---

# O que é um Ingress?

O Ingress é um conjunto de regras HTTP.

Ele informa ao NGINX:

> "Quando chegar uma requisição com determinado Host e determinado Path, envie-a para este Service."

O Ingress não recebe conexões.

Quem recebe conexões é o NGINX Ingress Controller.

---

# Estrutura Geral

Um Ingress possui aproximadamente esta estrutura.

```yaml
apiVersion:

kind:

metadata:

spec:

    ingressClassName

    tls

    rules
```

---

# apiVersion

Sempre.

```yaml
apiVersion: networking.k8s.io/v1
```

---

# kind

```yaml
kind: Ingress
```

---

# metadata

Exemplo.

```yaml
metadata:

  name: integrador-topdesk

  namespace: integrador-topdesk
```

---

# ingressClassName

Exemplo.

```yaml
ingressClassName: nginx
```

Esse campo informa qual controlador deverá interpretar esse Ingress.

No nosso ambiente utilizamos:

```
NGINX Ingress Controller
```

Se existissem outros controladores, cada um poderia utilizar uma classe diferente.

---

# rules

As regras representam o coração do Ingress.

Exemplo.

```yaml
rules:

- host:

    api.proativetec.com.br
```

Observe que o Ingress já conhece o domínio.

---

# Host

No nosso ambiente utilizamos.

```
api.proativetec.com.br
```

Quando uma requisição chega com outro Host.

Por exemplo.

```
teste.proativetec.com.br
```

essa regra não será utilizada.

---

# HTTP

Dentro do Host encontramos.

```yaml
http:
```

Agora começam as regras de roteamento.

---

# Paths

Exemplo.

```yaml
paths:
```

Cada Path representa uma aplicação.

Atualmente temos duas.

```
/topdesk
```

e

```
/hpe-suzano
```

Nada impede que amanhã existam:

```
/wireair
```

```
/onevision
```

```
/zabbix
```

Todos utilizando exatamente o mesmo domínio.

---

# path

Exemplo.

```yaml
path: /topdesk
```

Quando o usuário acessar.

```
https://api.proativetec.com.br/topdesk
```

essa regra será utilizada.

---

# pathType

No ambiente utilizamos.

```yaml
pathType: Prefix
```

Isso significa.

Tudo que começar por.

```
/topdesk
```

será encaminhado ao mesmo Service.

Exemplo.

```
/topdesk
```

```
/topdesk/login
```

```
/topdesk/api
```

```
/topdesk/api/v1.0/tasks
```

Todos correspondem à mesma regra.

---

# backend

Depois de localizar o Path.

O Ingress procura o Backend.

Exemplo.

```yaml
backend:
```

---

# Service

Exemplo.

```yaml
service:

    name: integrador-topdesk
```

Observe.

O Ingress conhece apenas o Service.

Nunca os Pods.

---

# Port

Exemplo.

```yaml
port:

    number: 80
```

Essa porta corresponde ao Service.

Não ao Gunicorn.

Fluxo.

```
Ingress

↓

Service

80

↓

Pod

8889
```

---

# TLS

Também utilizamos HTTPS.

Exemplo.

```yaml
tls:

- hosts:

  - api.proativetec.com.br

  secretName:

    api-proativetec-tls
```

O certificado encontra-se armazenado como um Secret Kubernetes.

---

# Como funciona uma requisição?

Vamos acompanhar uma requisição real.

```
https://api.proativetec.com.br/topdesk/api/v1.0/tasks
```

Primeiro.

```
Registro.br
```

↓

```
AWS DNS
```

↓

```
AWS NLB
```

↓

```
NGINX Ingress Controller
```

O NGINX verifica.

```
Host

api.proativetec.com.br
```

Depois.

```
Path

/topdesk
```

Consulta o Ingress.

Encontra.

```
Service

integrador-topdesk
```

Depois.

```
EndpointSlice
```

↓

```
Pod
```

↓

```
Gunicorn
```

↓

```
Flask
```

↓

```
internalintegrator.py
```

---

# Como coexistem Topdesk e HPE?

Observe.

```
api.proativetec.com.br
```

↓

```
/topdesk

↓

Service A
```

```
/hpe-suzano

↓

Service B
```

Embora o domínio seja o mesmo.

Cada aplicação possui:

- Deployment próprio
- Pods próprios
- Service próprio

Compartilhando apenas.

- NLB
- NGINX

---

# Adicionando um novo Integrador

Suponha.

```
WireAir
```

Bastaria criar.

```
Deployment

↓

Service

↓

Ingress
```

Com a regra.

```
/wireair
```

Não seria necessário.

- novo domínio;
- novo Load Balancer;
- novo NGINX.

Essa é uma das grandes vantagens dessa arquitetura.

---

# O que acontece se o Service não existir?

O Ingress continuará funcionando.

Entretanto.

```
NGINX

↓

Service inexistente

↓

HTTP 502
```

Esse é um erro comum durante implantações.

---

# O que acontece se não existirem Pods?

Fluxo.

```
Ingress

↓

Service

↓

EndpointSlice vazio

↓

503 Service Unavailable
```

---

# Troubleshooting

## Verificar Ingress

```bash
kubectl get ingress \
-n integrador-topdesk
```

---

## Ver detalhes

```bash
kubectl describe ingress \
integrador-topdesk \
-n integrador-topdesk
```

---

## Verificar regras

```bash
kubectl get ingress \
-o wide
```

---

## Verificar NGINX

```bash
kubectl get pods \
-n ingress-nginx
```

---

## Verificar logs

```bash
kubectl logs \
-n ingress-nginx \
deployment/ingress-nginx-controller
```

---

# Boas Práticas

✔ Um domínio para toda a plataforma.

✔ Separação por Paths.

✔ Um Service por aplicação.

✔ Um Deployment por aplicação.

✔ Um Ingress por aplicação.

✔ Certificados TLS centralizados.

✔ Nunca apontar um Ingress diretamente para Pods.

✔ Nunca utilizar NodePort para aplicações públicas.

---

# 24. NGINX Ingress Controller

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve o funcionamento do **NGINX Ingress Controller**, componente responsável por publicar aplicações HTTP/HTTPS executadas no Kubernetes.

Ao término da leitura o desenvolvedor compreenderá:

- o que é um Ingress Controller;
- por que o recurso Ingress sozinho não funciona;
- como o NGINX Ingress Controller interpreta os Ingresses;
- como novas aplicações passam a ser publicadas automaticamente;
- como o Controller se integra ao AWS Network Load Balancer.

---

# O que é um Ingress Controller?

Um erro muito comum é imaginar que o Kubernetes possui um servidor Web interno.

Na realidade isso não existe.

O Kubernetes apenas possui o recurso:

```
Ingress
```

Esse recurso contém somente regras.

Exemplo.

```
Host

↓

api.proativetec.com.br
```

↓

```
Path

↓

/topdesk
```

↓

```
Service

↓

integrador-topdesk
```

Entretanto o Kubernetes não sabe interpretar essas regras.

É exatamente essa a função do **Ingress Controller**.

---

# Ingress x Ingress Controller

Esses dois conceitos costumam ser confundidos.

## Ingress

É apenas um objeto Kubernetes.

Contém regras.

Não recebe conexões.

Não executa processos.

---

## Ingress Controller

É uma aplicação executando dentro do Cluster.

Recebe conexões.

Interpreta regras.

Encaminha requisições.

No nosso ambiente utilizamos:

```
NGINX Ingress Controller
```

---

# Arquitetura

```
Cliente

↓

AWS Network Load Balancer

↓

NGINX Ingress Controller

↓

Ingress

↓

Service

↓

Pod
```

Observe.

O Controller consulta o Ingress.

O Ingress não chama o Controller.

---

# Onde ele está instalado?

No ambiente atual.

```
Namespace

↓

ingress-nginx
```

Podemos verificar.

```bash
kubectl get pods \
-n ingress-nginx
```

Resultado semelhante.

```
ingress-nginx-controller
```

Esse Deployment é totalmente independente das aplicações.

---

# Deployment do Controller

Assim como qualquer aplicação Kubernetes, o Controller também possui.

```
Deployment

↓

ReplicaSet

↓

Pods
```

Ele é apenas mais uma aplicação do Cluster.

---

# O Service do Controller

Um detalhe muito importante.

O Controller possui um Service diferente dos demais.

```bash
kubectl get svc \
-n ingress-nginx
```

Resultado.

```
ingress-nginx-controller

TYPE

LoadBalancer
```

Observe.

Não é:

```
ClusterIP
```

É:

```
LoadBalancer
```

Esse detalhe muda completamente a arquitetura.

---

# Como surgiu o AWS Network Load Balancer?

Quando esse Service foi criado.

```
Type

↓

LoadBalancer
```

o Kubernetes enviou uma solicitação para a AWS.

Fluxo.

```
Service

↓

Cloud Provider AWS

↓

Criação do NLB
```

Automaticamente surgiu.

```
k8s-ingressn-ingressn-2f4d5d3114

↓

DNS público

↓

Internet
```

Nenhum recurso foi criado manualmente na AWS.

---

# O papel do NLB

O NLB possui apenas duas responsabilidades.

- receber conexões da Internet;

- encaminhá-las para o NGINX.

Ele não conhece:

- Ingress;

- Service;

- Pods.

---

# Como o Controller encontra novos Ingresses?

O Controller permanece observando continuamente o Kubernetes.

```
Kubernetes API

↓

Ingresses

↓

NGINX Controller
```

Sempre que um novo Ingress é criado.

```
kubectl apply
```

↓

```
Novo Ingress
```

↓

```
Controller detecta
```

↓

```
Atualiza configuração
```

Tudo ocorre automaticamente.

---

# O Controller utiliza Watch

Internamente o Controller utiliza a API Kubernetes.

```
Watch

↓

Ingress

↓

Service

↓

EndpointSlice

↓

Secret TLS
```

Sempre que algum desses recursos muda.

O Controller atualiza sua configuração.

Não é necessário reiniciar nada.

---

# Como o NGINX é configurado?

Imagine.

```
Ingress A

↓

/topdesk
```

```
Ingress B

↓

/hpe-suzano
```

O Controller gera automaticamente uma configuração equivalente.

```
server {

    location /topdesk {

        proxy_pass ...

    }

    location /hpe-suzano {

        proxy_pass ...

    }

}
```

Nenhum administrador precisa editar arquivos do NGINX.

Tudo é gerado automaticamente.

---

# Reload

Sempre que uma alteração ocorre.

```
Novo Ingress
```

↓

```
Controller gera configuração
```

↓

```
NGINX Reload
```

Esse Reload não interrompe conexões existentes.

Essa é uma das principais vantagens do NGINX.

---

# Certificados

O Controller também administra HTTPS.

Fluxo.

```
Secret TLS

↓

Ingress

↓

Controller

↓

NGINX
```

Quando um novo certificado é criado.

```
kubectl apply
```

↓

```
Secret
```

↓

```
Controller
```

↓

```
Reload
```

Nenhuma reinicialização é necessária.

---

# Como um novo Integrador é publicado?

Suponha.

```
Integrador WireAir
```

Criamos.

```
Deployment
```

↓

```
Service
```

↓

```
Ingress
```

O Controller detecta automaticamente.

```
Novo Ingress
```

↓

```
Nova configuração
```

↓

```
Aplicação disponível
```

Não é necessário alterar.

- NLB;

- DNS;

- NGINX.

---

# Alta Disponibilidade

O Controller também pode possuir múltiplas réplicas.

```
Deployment

↓

ReplicaSet

↓

Controller A

Controller B
```

Assim, a falha de um Pod não interrompe a publicação das aplicações.

---

# Troubleshooting

## Verificar Pods

```bash
kubectl get pods \
-n ingress-nginx
```

---

## Verificar Services

```bash
kubectl get svc \
-n ingress-nginx
```

---

## Verificar Logs

```bash
kubectl logs \
deployment/ingress-nginx-controller \
-n ingress-nginx
```

---

## Verificar Ingresses

```bash
kubectl get ingress \
-A
```

---

## Verificar Endpoints

```bash
kubectl get endpointslice \
-A
```

---

# Boas Práticas

✔ Manter apenas um Controller para toda a plataforma.

✔ Utilizar Paths para separar aplicações.

✔ Utilizar HTTPS em todas as aplicações públicas.

✔ Monitorar continuamente os Logs do Controller.

✔ Não editar manualmente a configuração do NGINX.

✔ Publicar aplicações apenas através de Ingress.

✔ Utilizar certificados armazenados como Secrets.

---

# 25. AWS Network Load Balancer (NLB)

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve detalhadamente o funcionamento do **AWS Network Load Balancer (NLB)** utilizado na plataforma da Proative.

Ao término da leitura o desenvolvedor deverá compreender:

- o que é um Load Balancer;
- quais tipos de Load Balancer existem na AWS;
- por que o Kubernetes criou automaticamente um NLB;
- como o NLB encaminha conexões para o Cluster Kubernetes;
- como ocorre o balanceamento entre os Worker Nodes;
- como o NLB se integra ao NGINX Ingress Controller.

---

# O que é um Load Balancer?

Um Load Balancer é um equipamento (ou serviço) responsável por distribuir conexões entre diversos servidores.

Sem Load Balancer:

```
                Cliente

                   │

                   ▼

               Servidor
```

Existe apenas um ponto de falha.

Caso esse servidor fique indisponível, toda a aplicação ficará inacessível.

---

# Utilizando um Load Balancer

```
                Cliente

                   │

                   ▼

             Load Balancer

             ┌─────┴─────┐

             ▼           ▼

         Servidor A   Servidor B
```

Agora qualquer servidor poderá atender às requisições.

Caso um servidor falhe, o outro continuará atendendo normalmente.

---

# Tipos de Load Balancer da AWS

Atualmente a AWS disponibiliza três tipos principais.

```
Classic Load Balancer (ELB)

Application Load Balancer (ALB)

Network Load Balancer (NLB)
```

Cada um possui características próprias.

---

# Classic Load Balancer (ELB)

Foi o primeiro balanceador disponibilizado pela AWS.

Hoje é considerado legado.

Características:

- suporta HTTP;
- suporta HTTPS;
- suporta TCP;
- poucas funcionalidades modernas.

Não é recomendado para novos projetos.

---

# Application Load Balancer (ALB)

Opera na Camada 7 (HTTP/HTTPS).

Possui recursos avançados.

Exemplos.

- Host Routing

- Path Routing

- Cookies

- WebSocket

- HTTP/2

- WAF

Ideal para aplicações Web.

---

# Network Load Balancer (NLB)

Opera na Camada 4 (TCP).

Características.

- extremamente rápido;

- baixíssima latência;

- milhões de conexões;

- IP fixo por zona de disponibilidade;

- preserva o endereço IP do cliente.

É exatamente esse tipo utilizado na nossa plataforma.

---

# Comparação

| Característica | ALB | NLB |
|----------------|-----|-----|
| Camada OSI | 7 | 4 |
| HTTP | ✔ | ✔ (TCP pass-through) |
| HTTPS | ✔ | ✔ |
| TCP | ✔ | ✔ |
| WebSocket | ✔ | ✔ |
| Menor latência | | ✔ |
| Preserva IP do cliente | | ✔ |

---

# Qual utilizamos?

No ambiente da Proative utilizamos.

```
AWS Network Load Balancer
```

Podemos verificar.

```bash
aws elbv2 describe-load-balancers
```

Resultado.

```
Type

network
```

Observe.

Não é.

```
application
```

É.

```
network
```

---

# Como o NLB foi criado?

Nenhum administrador entrou no Console AWS para criá-lo.

Ele foi criado automaticamente.

Fluxo.

```
Service

↓

Type LoadBalancer

↓

Cloud Provider AWS

↓

Criação automática do NLB
```

Tudo ocorreu automaticamente quando o Service do NGINX foi criado.

---

# O Service responsável

Podemos verificar.

```bash
kubectl get svc \
-n ingress-nginx
```

Resultado.

```
ingress-nginx-controller

TYPE

LoadBalancer
```

Esse Service originou o NLB.

---

# O DNS do NLB

A AWS atribuiu automaticamente.

```
k8s-ingressn-ingressn-2f4d5d3114-6d62b5d9a52120e3.elb.us-east-1.amazonaws.com
```

Esse DNS aponta para diversos endereços IP públicos.

Esses IPs podem mudar ao longo do tempo.

Por esse motivo nunca utilizamos IPs diretamente.

---

# Registro.br

O domínio.

```
api.proativetec.com.br
```

possui um registro.

```
CNAME
```

apontando para.

```
k8s-ingressn-ingressn-2f4d5d3114-6d62b5d9a52120e3.elb.us-east-1.amazonaws.com
```

Fluxo.

```
Registro.br

↓

DNS AWS

↓

NLB
```

---

# O que acontece quando um usuário acessa?

```
https://api.proativetec.com.br
```

Primeiro.

```
DNS

↓

Registro.br
```

↓

```
AWS DNS
```

↓

```
NLB
```

↓

```
Worker Node
```

↓

```
NGINX Ingress Controller
```

↓

```
Ingress
```

↓

```
Service
```

↓

```
Pod
```

---

# Como o NLB conhece os Nodes?

Quando o Kubernetes criou o Service.

```
Type

LoadBalancer
```

ele registrou automaticamente todos os Worker Nodes como Targets.

```
NLB

      │

 ┌────┴────┐

 ▼         ▼

Node A   Node B
```

Observe.

O NLB conhece Nodes.

Não conhece Pods.

---

# Health Check

O NLB monitora continuamente os Worker Nodes.

```
Node A

↓

Healthy
```

```
Node B

↓

Healthy
```

Caso um Node fique indisponível.

```
Node A

↓

Healthy
```

```
Node B

↓

Unhealthy
```

Todas as conexões passam automaticamente para o Node saudável.

---

# Alta Disponibilidade

O ambiente atual possui dois Worker Nodes.

```
NLB

     │

 ┌───┴────┐

 ▼        ▼

Node A  Node B

```

Se um Node falhar.

```
Node B

↓

Unhealthy
```

↓

```
Todo tráfego

↓

Node A
```

Quando o Node retornar.

Ele volta automaticamente ao balanceamento.

---

# Como o tráfego chega ao Pod?

Depois que o NLB encaminha a conexão.

```
Worker Node

↓

NGINX Ingress Controller

↓

Ingress

↓

Service

↓

EndpointSlice

↓

Pod
```

Observe que o NLB nunca conhece:

- Deployment;

- Service;

- Pod;

- EndpointSlice.

Esses conceitos pertencem ao Kubernetes.

---

# Vantagens do NLB

- Alta disponibilidade.

- Baixa latência.

- Balanceamento automático.

- Integração nativa com Kubernetes.

- Escalabilidade automática.

- Elimina ponto único de falha.

---

# Custos

O AWS Network Load Balancer possui cobrança baseada em:

- tempo de utilização;

- quantidade de conexões;

- processamento de dados.

Como compartilhamos um único NLB entre diversos integradores, reduzimos significativamente o custo da infraestrutura.

---

# Troubleshooting

## Listar NLB

```bash
aws elbv2 describe-load-balancers
```

---

## Ver detalhes

```bash
aws elbv2 describe-target-groups
```

---

## Ver Targets

```bash
aws elbv2 describe-target-health \
--target-group-arn <ARN>
```

---

## Ver Service

```bash
kubectl get svc \
-n ingress-nginx
```

---

## Ver External IP

```bash
kubectl get svc \
-n ingress-nginx \
-o wide
```

---

# Boas Práticas

✔ Compartilhar um único NLB para diversas aplicações.

✔ Nunca apontar o Registro.br para um endereço IP.

✔ Utilizar sempre o DNS do NLB.

✔ Monitorar a saúde dos Worker Nodes.

✔ Utilizar HTTPS em todas as aplicações públicas.

✔ Evitar criar um NLB para cada aplicação.

✔ Utilizar Ingress para separar aplicações.

---

# 26. Amazon Elastic Kubernetes Service (Amazon EKS)

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve detalhadamente o funcionamento interno do Amazon Elastic Kubernetes Service (Amazon EKS) utilizado na plataforma da Proative.

Ao término da leitura o desenvolvedor deverá compreender:

- como um Cluster Kubernetes é composto;
- quais componentes pertencem à AWS;
- quais componentes pertencem ao cliente;
- como nasce um Pod;
- como uma requisição percorre todo o Cluster;
- como o Kubernetes mantém a alta disponibilidade da aplicação.

---

# O que é o Amazon EKS?

O Amazon Elastic Kubernetes Service (Amazon EKS) é um serviço gerenciado da AWS que executa um Cluster Kubernetes.

Diferentemente de uma instalação manual, onde o administrador precisa instalar todos os componentes do Kubernetes, o Amazon EKS entrega o **Control Plane** totalmente gerenciado.

Isso reduz significativamente a complexidade operacional.

---

# Arquitetura Geral

```
                     Internet

                         │

                         ▼

               AWS Network Load Balancer

                         │

                         ▼

                Worker Node (EC2)

                         │

                NGINX Ingress Controller

                         │

                    Kubernetes

                         │

                Service / EndpointSlice

                         │

                         ▼

                       Pod

                         │

                    Gunicorn

                         │

                      Flask

                         │

                internalintegrator.py
```

---

# Componentes do Cluster

O Cluster Kubernetes é dividido em dois grandes blocos.

```
Amazon EKS

├── Control Plane
│
└── Worker Nodes
```

---

# Control Plane

O Control Plane representa o cérebro do Cluster.

Ele é responsável por tomar decisões.

No Amazon EKS ele é totalmente administrado pela AWS.

O cliente não possui acesso SSH a esses servidores.

---

## Componentes do Control Plane

```
Control Plane

├── kube-apiserver
├── etcd
├── kube-scheduler
└── kube-controller-manager
```

---

# kube-apiserver

É o ponto de entrada do Kubernetes.

Todo comando executado através do kubectl chega primeiro ao API Server.

Exemplo.

```bash
kubectl apply -f deployment.yaml
```

Fluxo.

```
kubectl

↓

kube-apiserver
```

Nenhum componente altera o Cluster diretamente.

Tudo passa pelo API Server.

---

# etcd

O etcd é o banco de dados do Kubernetes.

Ele armazena:

- Deployments;
- Services;
- Pods;
- ConfigMaps;
- Secrets;
- Ingresses;
- Namespaces;
- Nodes.

Em outras palavras.

Tudo que existe no Cluster encontra-se armazenado no etcd.

---

# kube-scheduler

Sempre que um novo Pod precisa ser criado.

O Scheduler decide.

```
Node A

ou

Node B
```

A decisão leva em consideração.

- CPU;
- Memória;
- Afinidade;
- Taints;
- Tolerations;
- Recursos disponíveis.

---

# kube-controller-manager

O Controller Manager monitora continuamente o estado do Cluster.

Exemplo.

```
Deployment

↓

Desejo

2 Pods
```

Situação atual.

```
Existe apenas

1 Pod
```

O Controller Manager detecta essa diferença.

↓

Solicita a criação de um novo Pod.

---

# Worker Nodes

Os Worker Nodes executam efetivamente os Pods.

No nosso ambiente existem dois Worker Nodes.

```
Cluster

      │

 ┌────┴────┐

 ▼         ▼

Node A   Node B
```

Cada Node é uma instância EC2.

---

# Componentes do Worker Node

Cada Worker Node possui.

```
Linux

↓

Container Runtime

↓

kubelet

↓

kube-proxy
```

---

# kubelet

O kubelet é o agente Kubernetes instalado em cada Node.

Ele recebe instruções do API Server.

Exemplo.

```
Criar Pod
```

↓

```
kubelet
```

↓

```
Container Runtime
```

↓

```
Novo Container
```

---

# Container Runtime

O Runtime é responsável por executar containers.

No EKS moderno normalmente utiliza-se.

```
containerd
```

Ele recebe uma imagem.

↓

Baixa do Amazon ECR.

↓

Inicia o Container.

---

# kube-proxy

O kube-proxy implementa o funcionamento dos Services.

Fluxo.

```
Service

↓

EndpointSlice

↓

Pod
```

Sempre que uma requisição chega ao ClusterIP.

O kube-proxy decide qual Pod deverá recebê-la.

---

# VPC

Todo o Cluster encontra-se dentro de uma Amazon VPC.

```
Amazon VPC

↓

Subnets

↓

Worker Nodes
```

A VPC fornece.

- isolamento;
- roteamento;
- segurança.

---

# Subnets

No nosso ambiente utilizamos múltiplas Availability Zones.

```
AZ A

↓

Node A
```

```
AZ B

↓

Node B
```

Caso uma Zona fique indisponível.

A outra continuará atendendo.

---

# Security Groups

Os Worker Nodes possuem Security Groups.

Eles controlam.

- portas abertas;
- origem das conexões;
- destino das conexões.

O NLB também possui Security Groups próprios.

---

# CoreDNS

O CoreDNS fornece resolução DNS dentro do Cluster.

Por exemplo.

```
mariadb.mariadb.svc.cluster.local
```

Esse nome é resolvido automaticamente.

Sem CoreDNS seria necessário utilizar IPs.

---

# Metrics Server

O Metrics Server coleta.

- CPU;
- Memória.

Essas informações são utilizadas por componentes como o Horizontal Pod Autoscaler (HPA).

---

# Como nasce um Pod?

Quando executamos.

```bash
kubectl apply -f deployment.yaml
```

ocorre.

```
Deployment

↓

API Server

↓

etcd

↓

Controller Manager

↓

Scheduler

↓

Node escolhido

↓

kubelet

↓

containerd

↓

Download da imagem

↓

Container

↓

Pod Running
```

Todo esse processo normalmente ocorre em poucos segundos.

---

# Como nasce uma atualização?

Suponha.

```
Imagem

0.1.4
```

↓

```
Imagem

0.1.5
```

Após.

```bash
kubectl apply
```

O fluxo é.

```
Deployment

↓

Novo ReplicaSet

↓

Novo Pod

↓

Readiness Probe

↓

Recebe tráfego

↓

Remove Pod antigo

↓

Novo Pod

↓

Readiness Probe

↓

Remove último Pod antigo
```

Isso é o Rolling Update.

---

# Como nasce uma requisição?

Vamos acompanhar uma requisição real.

```
Cliente

↓

Registro.br

↓

AWS DNS

↓

NLB

↓

Worker Node

↓

NGINX

↓

Ingress

↓

Service

↓

EndpointSlice

↓

Pod

↓

Gunicorn

↓

Flask

↓

internalintegrator.py

↓

MariaDB
```

Essa é exatamente a arquitetura utilizada pelo Integrador Topdesk.

---

# Como o Cluster mantém a disponibilidade?

Imagine.

```
Deployment

2 Pods
```

Um Pod falha.

```
Pod A

Running
```

```
Pod B

Erro
```

O Controller Manager detecta.

↓

ReplicaSet.

↓

Scheduler.

↓

Novo Node.

↓

Novo Pod.

Tudo automaticamente.

---

# Como um Node falha?

Imagine.

```
Node B

↓

Desligou
```

O Kubernetes detecta.

↓

Todos os Pods daquele Node.

↓

Scheduler.

↓

Criação em outro Node.

Sem intervenção manual.

---

# O papel do kubectl

O kubectl nunca conversa diretamente com Pods.

Ele conversa apenas com.

```
API Server
```

Exemplo.

```bash
kubectl get pods
```

↓

```
API Server
```

↓

```
etcd
```

↓

Resposta.

---

# Resumo da Arquitetura

```
kubectl

↓

API Server

↓

etcd

↓

Controller Manager

↓

Scheduler

↓

Worker Node

↓

kubelet

↓

containerd

↓

Pod

↓

Aplicação
```

---

# Boas Práticas

✔ Nunca alterar recursos diretamente nos Worker Nodes.

✔ Utilizar apenas kubectl para administrar o Cluster.

✔ Manter os manifests versionados no GitHub.

✔ Nunca acessar Pods por IP.

✔ Distribuir Pods entre múltiplos Nodes.

✔ Utilizar Readiness e Liveness Probes.

✔ Monitorar continuamente os Nodes.

✔ Utilizar Rolling Updates para todas as implantações.

---

# 27. Troubleshooting e Diagnóstico do Cluster Kubernetes

**Versão:** 1.0

---

# Objetivo

Este capítulo apresenta os procedimentos de diagnóstico e troubleshooting utilizados na administração do ambiente Kubernetes da Proative.

Os exemplos foram baseados na operação do Integrador Topdesk e dos demais integradores implantados no Amazon EKS.

Ao término deste capítulo o administrador deverá ser capaz de diagnosticar rapidamente problemas relacionados a:

- Pods
- Deployments
- Services
- Ingress
- NGINX Ingress Controller
- Amazon ECR
- Amazon EKS
- MariaDB
- ConfigMap
- Secret
- DNS
- Network Load Balancer

---

# Filosofia de Diagnóstico

Sempre siga a mesma ordem.

Nunca comece analisando a aplicação.

Comece pela infraestrutura.

```
Cliente

↓

DNS

↓

NLB

↓

Ingress Controller

↓

Ingress

↓

Service

↓

EndpointSlice

↓

Pod

↓

Container

↓

Gunicorn

↓

Flask

↓

Aplicação

↓

Banco
```

Em aproximadamente 90% dos problemas, a falha será encontrada antes mesmo de chegar ao código Python.

---

# Diagnóstico Geral

## O Cluster está funcionando?

```bash
kubectl get nodes
```

Resultado esperado.

```
STATUS

Ready
```

Todos os Nodes devem estar em estado Ready.

---

## Os namespaces existem?

```bash
kubectl get ns
```

Esperado.

```
ingress-nginx

mariadb

integrador-topdesk

integrador-hpe-suzano
```

---

# Diagnóstico dos Pods

## Listar Pods

```bash
kubectl get pods -A
```

---

## Listar Pods do Integrador

```bash
kubectl get pods \
-n integrador-topdesk \
-o wide
```

Verificar:

- READY
- STATUS
- RESTARTS
- NODE
- IP

---

## Descrever um Pod

```bash
kubectl describe pod <POD> \
-n integrador-topdesk
```

Este comando mostra:

- eventos;
- montagem de volumes;
- ConfigMaps;
- Secrets;
- imagens;
- probes.

É um dos comandos mais importantes do Kubernetes.

---

## Logs

Últimas linhas.

```bash
kubectl logs \
<POD> \
-n integrador-topdesk \
--tail=100
```

Logs contínuos.

```bash
kubectl logs -f \
<POD> \
-n integrador-topdesk
```

---

# Diagnóstico do Deployment

Listar.

```bash
kubectl get deployment \
-n integrador-topdesk
```

Detalhes.

```bash
kubectl describe deployment \
integrador-topdesk \
-n integrador-topdesk
```

---

## Ver imagem utilizada

```bash
kubectl get deployment \
integrador-topdesk \
-n integrador-topdesk \
-o jsonpath='{.spec.template.spec.containers[0].image}'
```

Muito útil para confirmar a versão implantada.

---

# Rollout

Ver andamento.

```bash
kubectl rollout status \
deployment/integrador-topdesk \
-n integrador-topdesk
```

Histórico.

```bash
kubectl rollout history \
deployment/integrador-topdesk \
-n integrador-topdesk
```

Rollback.

```bash
kubectl rollout undo \
deployment/integrador-topdesk \
-n integrador-topdesk
```

---

# Diagnóstico do Service

Listar.

```bash
kubectl get svc \
-n integrador-topdesk
```

Detalhes.

```bash
kubectl describe svc \
integrador-topdesk \
-n integrador-topdesk
```

Verificar:

- ClusterIP
- Port
- TargetPort
- Selector

---

# Diagnóstico do EndpointSlice

```bash
kubectl get endpointslice \
-n integrador-topdesk
```

Esperado.

```
10.50.xx.xx

10.50.yy.yy
```

Se não existirem Endpoints:

- verificar Labels;
- verificar Pods;
- verificar Selector.

---

# Diagnóstico do Ingress

Listar.

```bash
kubectl get ingress -A
```

Detalhes.

```bash
kubectl describe ingress \
integrador-topdesk \
-n integrador-topdesk
```

Verificar:

- Host
- Path
- Backend
- TLS

---

# Diagnóstico do NGINX

Pods.

```bash
kubectl get pods \
-n ingress-nginx
```

Logs.

```bash
kubectl logs \
deployment/ingress-nginx-controller \
-n ingress-nginx
```

---

# Diagnóstico do NLB

Listar.

```bash
aws elbv2 describe-load-balancers
```

Ver Target Groups.

```bash
aws elbv2 describe-target-groups
```

Ver Health.

```bash
aws elbv2 describe-target-health \
--target-group-arn <ARN>
```

---

# Diagnóstico do DNS

Resolver domínio.

```bash
dig api.proativetec.com.br
```

Esperado.

```
CNAME

↓

NLB
```

---

# Diagnóstico do MariaDB

Ver Pod.

```bash
kubectl get pods \
-n mariadb
```

Entrar.

```bash
kubectl exec -it \
-n mariadb \
mariadb-0 \
-- sh
```

Entrar no MySQL.

```bash
mysql \
-u integrador_topdesk \
-p
```

---

# Diagnóstico de ConfigMap

Listar.

```bash
kubectl get configmap \
-n integrador-topdesk
```

Visualizar.

```bash
kubectl describe configmap \
integrador-topdesk-config \
-n integrador-topdesk
```

---

# Diagnóstico de Secret

Listar.

```bash
kubectl get secret \
-n integrador-topdesk
```

Visualizar.

```bash
kubectl describe secret \
integrador-topdesk-secret \
-n integrador-topdesk
```

---

# Verificar variáveis

```bash
kubectl exec \
-it deployment/integrador-topdesk \
-n integrador-topdesk \
-- env
```

---

# Teste de DNS Interno

```bash
kubectl exec \
-it deployment/integrador-topdesk \
-n integrador-topdesk \
-- ping mariadb.mariadb.svc.cluster.local
```

Ou.

```bash
nslookup mariadb.mariadb.svc.cluster.local
```

---

# Entrando em um Pod

Shell.

```bash
kubectl exec \
-it \
deployment/integrador-topdesk \
-n integrador-topdesk \
-- sh
```

---

# Estados mais comuns dos Pods

## Running

Tudo funcionando.

---

## Pending

O Scheduler não conseguiu criar o Pod.

Verificar:

- CPU
- memória
- taints
- volumes

---

## CrashLoopBackOff

A aplicação inicia e termina repetidamente.

Verificar:

```bash
kubectl logs
```

---

## ImagePullBackOff

O Kubernetes não conseguiu baixar a imagem.

Verificar:

- Tag
- Amazon ECR
- autenticação

---

## ErrImagePull

Imagem inexistente.

Normalmente:

Tag incorreta.

---

## OOMKilled

O processo consumiu mais memória do que o limite permitido.

Verificar:

```yaml
resources
```

---

# Fluxo de Diagnóstico

```
Node Ready?

↓

Pods Running?

↓

Deployment OK?

↓

Service OK?

↓

EndpointSlice OK?

↓

Ingress OK?

↓

NGINX OK?

↓

DNS OK?

↓

Banco OK?

↓

Logs

↓

Aplicação
```

Seguindo essa sequência, praticamente todos os problemas encontrados durante a implantação dos integradores podem ser diagnosticados rapidamente.

---

# Os 20 comandos mais utilizados

| Objetivo | Comando |
|----------|----------|
| Ver Nodes | kubectl get nodes |
| Ver Pods | kubectl get pods -A |
| Ver Deployment | kubectl get deployment |
| Ver Service | kubectl get svc |
| Ver Ingress | kubectl get ingress |
| Ver EndpointSlice | kubectl get endpointslice |
| Ver Logs | kubectl logs |
| Ver Describe | kubectl describe |
| Rollout | kubectl rollout status |
| Rollback | kubectl rollout undo |
| Entrar no Pod | kubectl exec -- sh |
| Variáveis | env |
| DNS | dig |
| ConfigMap | kubectl describe configmap |
| Secret | kubectl describe secret |
| MariaDB | kubectl exec mariadb-0 |
| NLB | aws elbv2 describe-load-balancers |
| ECR | aws ecr describe-images |
| Eventos | kubectl get events |
| Todos os recursos | kubectl get all |

---

# Boas Práticas

✔ Sempre começar pelos Nodes.

✔ Nunca iniciar o diagnóstico pelo código Python.

✔ Verificar Events antes dos Logs.

✔ Confirmar a imagem implantada.

✔ Confirmar o EndpointSlice.

✔ Confirmar o Ingress.

✔ Confirmar o NLB.

✔ Confirmar o DNS.

✔ Somente então investigar a aplicação.

---

# 28. Runbook de Operação Diária da Plataforma

**Versão:** 1.0

---

# Objetivo

Este documento descreve os procedimentos operacionais diários para administração da plataforma executada no Amazon EKS.

O objetivo é permitir que qualquer administrador consiga verificar rapidamente a saúde do ambiente, implantar novas versões, diagnosticar problemas e restaurar serviços em caso de falhas.

Este Runbook deve ser utilizado como referência durante a operação diária da plataforma.

Todos os comandos devem ser executados a partir do servidor Linux de administração.

---

# Arquitetura Operacional

Atualmente a plataforma é composta por:

```text
Internet

↓

Registro.br

↓

AWS Network Load Balancer

↓

NGINX Ingress Controller

↓

Amazon EKS

↓

Namespaces

    ingress-nginx

    mariadb

    integrador-topdesk

    integrador-hpe-suzano

↓

Pods

↓

MariaDB
```

---

# Início do Expediente

Todo início de expediente recomenda-se executar a sequência abaixo.

---

## 1. Verificar os Nodes

```bash
kubectl get nodes
```

Resultado esperado:

```text
STATUS

Ready
```

Todos os Nodes devem estar disponíveis.

Para obter informações adicionais:

```bash
kubectl get nodes -o wide
```

---

## 2. Verificar os Deployments

```bash
kubectl get deployment -A
```

Esperado:

```text
READY

2/2
```

ou:

```text
1/1
```

Nenhum Deployment deve possuir réplicas indisponíveis.

Para verificar especificamente os integradores:

```bash
kubectl get deployment \
  -n integrador-topdesk
```

```bash
kubectl get deployment \
  -n integrador-hpe-suzano
```

---

## 3. Verificar os Pods

```bash
kubectl get pods -A -o wide
```

Confirmar:

- `STATUS` igual a `Running`;
- `READY` igual a `1/1`;
- `RESTARTS` estável;
- Pods distribuídos entre os Worker Nodes, quando possível.

Caso exista aumento inesperado de `RESTARTS`, investigar imediatamente.

---

## 4. Verificar Services

```bash
kubectl get svc -A
```

Confirmar:

- Services internos do tipo `ClusterIP`;
- Service do NGINX do tipo `LoadBalancer`;
- portas e `targetPorts` corretas.

Os Endpoints dos Services devem ser verificados através dos respectivos EndpointSlices.

---

## 5. Verificar EndpointSlices

```bash
kubectl get endpointslice -A
```

Confirmar que todos os Services das aplicações possuem Endpoints.

Exemplo para o Integrador Topdesk:

```bash
kubectl get endpointslice \
  -n integrador-topdesk \
  -l kubernetes.io/service-name=integrador-topdesk \
  -o wide
```

Devem aparecer os endereços IP dos Pods ativos.

---

## 6. Verificar Ingress

```bash
kubectl get ingress -A
```

Confirmar:

- Host;
- Path;
- endereço;
- TLS;
- Service de destino.

Para obter detalhes do Ingress do Integrador Topdesk:

```bash
kubectl describe ingress \
  integrador-topdesk \
  -n integrador-topdesk
```

---

## 7. Verificar o NGINX

```bash
kubectl get pods \
  -n ingress-nginx
```

Esperado:

```text
Running
```

Verificar também o Service:

```bash
kubectl get svc \
  -n ingress-nginx \
  -o wide
```

---

## 8. Verificar o MariaDB

```bash
kubectl get pods \
  -n mariadb
```

Esperado:

```text
Running
```

Verificar também o Service:

```bash
kubectl get svc \
  -n mariadb
```

---

## 9. Verificar o espaço em disco

Na máquina Linux de administração:

```bash
df -h
```

Para diagnosticar um Worker Node:

```bash
kubectl debug node/<NODE>
```

Depois de entrar no ambiente de depuração, o sistema de arquivos do Node normalmente poderá ser consultado em:

```bash
df -h /host
```

---

## 10. Verificar utilização de CPU

Caso o Metrics Server esteja instalado:

```bash
kubectl top nodes
```

---

## 11. Verificar memória

```bash
kubectl top pods -A
```

Para exibir apenas os Pods do Integrador Topdesk:

```bash
kubectl top pods \
  -n integrador-topdesk
```

---

# Checklist Diário

| Item | Verificar |
|---|---|
| Nodes | `Ready` |
| Pods | `Running` |
| Deployments | Réplicas `READY` |
| Services | Portas e tipos corretos |
| EndpointSlices | Possuem Endpoints |
| Ingress | Host, Path e TLS corretos |
| NGINX | `Running` |
| MariaDB | `Running` |
| CPU | Dentro do esperado |
| Memória | Dentro do esperado |
| Reinicializações | Sem aumento inesperado |
| Health Check | HTTP 200 |

---

# Checklist Semanal

Executar os procedimentos abaixo.

---

## Revisar imagens Docker

```bash
sudo docker image ls
```

Remover somente imagens que não estejam sendo utilizadas e que não sejam necessárias para testes ou rollback local.

Para visualizar o espaço ocupado:

```bash
sudo docker system df
```

---

## Revisar imagens no Amazon ECR

```bash
aws ecr list-images \
  --profile proative \
  --region us-east-1 \
  --repository-name integrador-topdesk
```

Avaliar a remoção de versões muito antigas, preservando:

- versões atualmente implantadas;
- versões necessárias para rollback;
- versões associadas a Releases oficiais.

---

## Revisar logs

```bash
kubectl logs \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  --prefix \
  --tail=1000
```

Verificar:

- Exceptions;
- Tracebacks;
- Timeouts;
- falhas de autenticação;
- erros de conexão com o MariaDB;
- falhas de comunicação com o Topdesk.

---

## Revisar reinicializações

```bash
kubectl get pods -A
```

Analisar a coluna:

```text
RESTARTS
```

Caso um Pod tenha sido reiniciado, consultar os logs da instância anterior:

```bash
kubectl logs \
  <NOME_DO_POD> \
  -n <NAMESPACE> \
  --previous
```

---

## Revisar certificados

Verificar o Secret TLS utilizado pelo Ingress:

```bash
kubectl get secret api-proativetec-tls \
  -n integrador-topdesk
```

Para consultar a validade do certificado público:

```bash
echo |
openssl s_client \
  -connect api.proativetec.com.br:443 \
  -servername api.proativetec.com.br \
  2>/dev/null |
openssl x509 \
  -noout \
  -subject \
  -issuer \
  -dates
```

---

# Checklist Mensal

- Atualizar a documentação.
- Revisar Branches Git.
- Revisar Tags Git.
- Revisar Tags Docker.
- Revisar versões implantadas.
- Revisar usuários AWS.
- Revisar usuários GitHub.
- Revisar permissões Kubernetes.
- Revisar Secrets.
- Revisar certificados TLS.
- Revisar backups.
- Executar teste de restauração.
- Revisar consumo de armazenamento do Amazon ECR.
- Revisar consumo de recursos dos Worker Nodes.

---

# Atualização do Código-Fonte da Aplicação

Este procedimento deve ser executado quando houver alteração em arquivos da aplicação, como:

```text
app/bin/internalintegrator.py
```

Como o código-fonte faz parte da imagem Docker, uma alteração em qualquer arquivo Python exige:

1. validação do código;
2. construção de uma nova imagem Docker;
3. publicação no Amazon ECR;
4. atualização do Deployment;
5. Rolling Update no Amazon EKS;
6. testes;
7. atualização do GitHub.

---

## 1. Acessar o diretório do projeto

```bash
cd /opt/proative/integrador-topdesk
```

---

## 2. Verificar o estado atual do Git

```bash
git status
```

Antes de iniciar uma nova alteração, o resultado recomendado é:

```text
nothing to commit, working tree clean
```

---

## 3. Atualizar o repositório local

```bash
git switch main
git pull --ff-only origin main
```

---

## 4. Criar uma Branch

Para uma correção:

```bash
git switch -c fix/descricao-da-correcao
```

Para uma nova funcionalidade:

```bash
git switch -c feature/descricao-da-funcionalidade
```

---

## 5. Alterar o código-fonte

Exemplo:

```bash
nano app/bin/internalintegrator.py
```

Após salvar, revisar as modificações:

```bash
git diff
```

---

## 6. Validar a sintaxe Python

Validar o arquivo principal:

```bash
python3 -m py_compile \
  app/bin/internalintegrator.py
```

Validar todos os arquivos Python:

```bash
python3 -m compileall app
```

A ausência de mensagens de erro indica que não foram encontrados erros de sintaxe.

Remover os diretórios `__pycache__` gerados pela validação:

```bash
find app \
  -type d \
  -name '__pycache__' \
  -prune \
  -exec rm -rf {} +
```

---

## 7. Verificar a versão implantada

```bash
kubectl get deployment integrador-topdesk \
  -n integrador-topdesk \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Exemplo:

```text
029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.1
```

---

## 8. Definir a nova versão

Exemplo:

```bash
export APP_VERSION=0.1.2
```

Confirmar:

```bash
echo "${APP_VERSION}"
```

Nunca reutilizar uma Tag já publicada no Amazon ECR.

---

## 9. Construir a imagem Docker

```bash
sudo docker build \
  -t integrador-topdesk:${APP_VERSION} \
  .
```

Verificar:

```bash
sudo docker image ls |
grep integrador-topdesk
```

---

## 10. Autenticar no Amazon ECR

```bash
aws ecr get-login-password \
  --profile proative \
  --region us-east-1 |
sudo docker login \
  --username AWS \
  --password-stdin \
  029142736054.dkr.ecr.us-east-1.amazonaws.com
```

Resultado esperado:

```text
Login Succeeded
```

Caso o ambiente não utilize o perfil AWS chamado `proative`, remover:

```text
--profile proative
```

---

## 11. Criar a Tag para o Amazon ECR

```bash
sudo docker tag \
  integrador-topdesk:${APP_VERSION} \
  029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:${APP_VERSION}
```

---

## 12. Publicar a imagem

```bash
sudo docker push \
  029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:${APP_VERSION}
```

---

## 13. Confirmar a imagem no Amazon ECR

```bash
aws ecr describe-images \
  --profile proative \
  --region us-east-1 \
  --repository-name integrador-topdesk \
  --image-ids imageTag=${APP_VERSION}
```

Visualização resumida:

```bash
aws ecr describe-images \
  --profile proative \
  --region us-east-1 \
  --repository-name integrador-topdesk \
  --image-ids imageTag=${APP_VERSION} \
  --query 'imageDetails[0].{Tags:imageTags,PushedAt:imagePushedAt,Digest:imageDigest}' \
  --output table
```

---

## 14. Atualizar o `deployment.yaml`

```bash
nano deployment.yaml
```

Alterar:

```yaml
image: 029142736054.dkr.ecr.us-east-1.amazonaws.com/integrador-topdesk:0.1.2
```

Confirmar também:

```yaml
replicas: 2
```

Revisar:

```bash
git diff -- deployment.yaml
```

---

## 15. Validar o Deployment

```bash
kubectl apply \
  --dry-run=server \
  -f deployment.yaml
```

Visualizar as diferenças:

```bash
kubectl diff \
  -f deployment.yaml
```

O `kubectl diff` pode retornar código de saída `1` quando existem diferenças. Isso não significa necessariamente falha.

---

## 16. Aplicar o Deployment

```bash
kubectl apply \
  -f deployment.yaml
```

---

## 17. Acompanhar o Rolling Update

```bash
kubectl rollout status \
  deployment/integrador-topdesk \
  -n integrador-topdesk \
  --timeout=180s
```

Resultado esperado:

```text
deployment "integrador-topdesk" successfully rolled out
```

---

## 18. Verificar o Deployment

```bash
kubectl get deployment integrador-topdesk \
  -n integrador-topdesk
```

Resultado esperado:

```text
READY   UP-TO-DATE   AVAILABLE
2/2     2            2
```

---

## 19. Verificar os Pods

```bash
kubectl get pods \
  -n integrador-topdesk \
  -o wide
```

Confirmar:

- dois Pods;
- `READY` igual a `1/1`;
- `STATUS` igual a `Running`;
- ausência de reinicializações inesperadas.

---

## 20. Confirmar a imagem de cada Pod

```bash
kubectl get pods \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.spec.containers[0].image}{"\n"}{end}'
```

Todos os Pods devem utilizar a nova versão.

---

## 21. Verificar o EndpointSlice

```bash
kubectl get endpointslice \
  -n integrador-topdesk \
  -l kubernetes.io/service-name=integrador-topdesk \
  -o wide
```

Devem aparecer os endereços IP dos dois Pods.

---

## 22. Testar internamente

```bash
kubectl run curl-test \
  --rm \
  -it \
  --restart=Never \
  --image=curlimages/curl \
  -n integrador-topdesk \
  -- curl -sS \
  -w '\nHTTP_STATUS=%{http_code}\n' \
  http://integrador-topdesk/health
```

Resultado esperado:

```text
OK
HTTP_STATUS=200
```

---

## 23. Testar externamente

```bash
curl -sS \
  https://api.proativetec.com.br/topdesk/health \
  -w '\nHTTP_STATUS=%{http_code}\n'
```

Resultado esperado:

```text
OK
HTTP_STATUS=200
```

---

## 24. Testar uma rota autenticada

Obter temporariamente o usuário:

```bash
BASIC_USER="$(
  kubectl get secret integrador-topdesk-secret \
    -n integrador-topdesk \
    -o jsonpath='{.data.API_BASIC_USER}' |
  base64 -d
)"
```

Obter temporariamente a senha:

```bash
BASIC_PASSWORD="$(
  kubectl get secret integrador-topdesk-secret \
    -n integrador-topdesk \
    -o jsonpath='{.data.API_BASIC_PASSWORD}' |
  base64 -d
)"
```

Executar o teste:

```bash
curl -sS \
  -u "${BASIC_USER}:${BASIC_PASSWORD}" \
  https://api.proativetec.com.br/topdesk/api/v1.0/tasks/ticket/TESTE \
  -w '\nHTTP_STATUS=%{http_code}\n'
```

Remover as variáveis da sessão:

```bash
unset BASIC_USER
unset BASIC_PASSWORD
```

---

## 25. Verificar os logs

```bash
kubectl logs \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  --prefix \
  --tail=200
```

Acompanhar em tempo real:

```bash
kubectl logs \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  --prefix \
  --tail=100 \
  -f
```

Interromper com:

```text
Ctrl+C
```

---

## 26. Verificar os eventos

```bash
kubectl get events \
  -n integrador-topdesk \
  --sort-by='.lastTimestamp'
```

---

## 27. Atualizar o GitHub

Verificar:

```bash
git status
```

Adicionar os arquivos alterados:

```bash
git add \
  app/bin/internalintegrator.py \
  deployment.yaml \
  README.md
```

Adicionar somente os arquivos que realmente sofreram alteração.

Criar o commit:

```bash
git commit \
  -m "fix: descreve a alteração realizada"
```

Publicar a Branch:

```bash
git push \
  -u origin \
  fix/descricao-da-correcao
```

Após o merge:

```bash
git switch main
git pull --ff-only origin main
```

---

## 28. Criar a Tag Git

```bash
git tag \
  -a v${APP_VERSION} \
  -m "Versão ${APP_VERSION}"
```

Publicar:

```bash
git push origin v${APP_VERSION}
```

---

# Alteração do ConfigMap

Este procedimento deve ser utilizado quando houver alteração em configurações não sensíveis, como:

```text
APP_NAME
ROOT_PATH
DEBUG
LOG_FILE
TOPDESK_BASE_URL
DB_HOST
DB_PORT
DB_NAME
DB_USER
ATTACHES_PATH
```

Uma alteração no ConfigMap não exige:

- construção de imagem Docker;
- nova Tag Docker;
- Push para o Amazon ECR;
- alteração da imagem do Deployment.

Entretanto, como o ConfigMap é carregado como variável de ambiente durante a criação do container, os Pods devem ser reiniciados.

---

## 1. Acessar o projeto

```bash
cd /opt/proative/integrador-topdesk
```

---

## 2. Atualizar a árvore Git

```bash
git switch main
git pull --ff-only origin main
```

---

## 3. Criar uma Branch

```bash
git switch -c config/atualiza-configmap
```

---

## 4. Editar o ConfigMap

```bash
nano configmap.yaml
```

---

## 5. Verificar as alterações

```bash
git diff -- configmap.yaml
```

---

## 6. Validar o manifesto

```bash
kubectl apply \
  --dry-run=server \
  -f configmap.yaml
```

Visualizar as diferenças:

```bash
kubectl diff \
  -f configmap.yaml
```

---

## 7. Aplicar o ConfigMap

```bash
kubectl apply \
  -f configmap.yaml
```

---

## 8. Confirmar o ConfigMap

```bash
kubectl get configmap integrador-topdesk-config \
  -n integrador-topdesk \
  -o yaml
```

---

## 9. Reiniciar gradualmente os Pods

```bash
kubectl rollout restart \
  deployment/integrador-topdesk \
  -n integrador-topdesk
```

---

## 10. Acompanhar o restart

```bash
kubectl rollout status \
  deployment/integrador-topdesk \
  -n integrador-topdesk \
  --timeout=180s
```

---

## 11. Verificar os Pods

```bash
kubectl get pods \
  -n integrador-topdesk \
  -o wide
```

---

## 12. Confirmar a variável alterada

Exemplo para `ROOT_PATH`:

```bash
kubectl exec \
  -n integrador-topdesk \
  deployment/integrador-topdesk \
  -- printenv ROOT_PATH
```

Exemplo para `DB_HOST`:

```bash
kubectl exec \
  -n integrador-topdesk \
  deployment/integrador-topdesk \
  -- printenv DB_HOST
```

---

## 13. Testar a aplicação

```bash
curl -sS \
  https://api.proativetec.com.br/topdesk/health \
  -w '\nHTTP_STATUS=%{http_code}\n'
```

---

## 14. Verificar os logs

```bash
kubectl logs \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  --prefix \
  --tail=200
```

---

## 15. Atualizar o GitHub

```bash
git add \
  configmap.yaml \
  README.md
```

```bash
git commit \
  -m "config: atualiza ConfigMap do integrador Topdesk"
```

```bash
git push \
  -u origin \
  config/atualiza-configmap
```

---

# Alteração do Secret

Este procedimento deve ser utilizado quando houver alteração em informações sensíveis, como:

```text
DB_PASSWORD
API_BASIC_USER
API_BASIC_PASSWORD
TOPDESK_PASSWORD
TOKEN
ACCESS_KEY
SECRET_KEY
```

Uma alteração no Secret não exige:

- construção de imagem Docker;
- nova Tag Docker;
- Push para o Amazon ECR;
- alteração da imagem no Deployment.

Porém, como os valores são carregados durante a criação do container, os Pods devem ser reiniciados.

O arquivo com valores reais não deve ser enviado ao GitHub.

---

## 1. Acessar o projeto

```bash
cd /opt/proative/integrador-topdesk
```

---

## 2. Confirmar que o arquivo está no `.gitignore`

```bash
grep -nE 'secret\.env|\.env' \
  .gitignore
```

Caso as regras não existam:

```bash
printf '\nsecret.env\n*.secret.env\n.env\n' \
  >> .gitignore
```

---

## 3. Fazer backup seguro do Secret atual

Definir permissões restritivas:

```bash
umask 077
```

Exportar:

```bash
kubectl get secret integrador-topdesk-secret \
  -n integrador-topdesk \
  -o yaml \
  > "${HOME}/integrador-topdesk-secret-backup-$(date +%Y%m%d-%H%M%S).yaml"
```

Esse arquivo contém dados sensíveis codificados em Base64 e deve permanecer protegido.

---

## 4. Editar o arquivo local

```bash
nano secret.env
```

Exemplo:

```text
DB_PASSWORD=valor_real
API_BASIC_USER=opmonadmin
API_BASIC_PASSWORD=valor_real
```

Evitar espaços antes ou depois do sinal `=`.

---

## 5. Verificar somente os nomes das variáveis

```bash
sed -E 's/=.*/=<oculto>/' \
  secret.env
```

---

## 6. Validar a geração do Secret

```bash
kubectl create secret generic integrador-topdesk-secret \
  -n integrador-topdesk \
  --from-env-file=secret.env \
  --dry-run=client \
  -o yaml \
  > /tmp/integrador-topdesk-secret.yaml
```

Verificar somente as chaves:

```bash
grep -E '^  [A-Za-z_][A-Za-z0-9_]*:' \
  /tmp/integrador-topdesk-secret.yaml
```

---

## 7. Aplicar o Secret

```bash
kubectl create secret generic integrador-topdesk-secret \
  -n integrador-topdesk \
  --from-env-file=secret.env \
  --dry-run=client \
  -o yaml |
kubectl apply -f -
```

---

## 8. Remover o arquivo temporário

```bash
rm -f \
  /tmp/integrador-topdesk-secret.yaml
```

---

## 9. Confirmar somente os nomes das chaves

```bash
kubectl get secret integrador-topdesk-secret \
  -n integrador-topdesk \
  -o json |
python3 -c '
import json
import sys

secret = json.load(sys.stdin)

for key in sorted(secret.get("data", {})):
    print(key)
'
```

---

## 10. Reiniciar gradualmente os Pods

```bash
kubectl rollout restart \
  deployment/integrador-topdesk \
  -n integrador-topdesk
```

---

## 11. Acompanhar o restart

```bash
kubectl rollout status \
  deployment/integrador-topdesk \
  -n integrador-topdesk \
  --timeout=180s
```

---

## 12. Verificar os Pods

```bash
kubectl get pods \
  -n integrador-topdesk \
  -o wide
```

---

## 13. Confirmar que as variáveis existem

Sem revelar seus valores:

```bash
kubectl exec \
  -n integrador-topdesk \
  deployment/integrador-topdesk \
  -- sh -c '
    for variable in DB_PASSWORD API_BASIC_USER API_BASIC_PASSWORD; do
        if printenv "$variable" >/dev/null 2>&1; then
            echo "$variable definida"
        else
            echo "$variable AUSENTE"
        fi
    done
  '
```

---

## 14. Testar a autenticação

Carregar temporariamente o usuário:

```bash
BASIC_USER="$(
  kubectl get secret integrador-topdesk-secret \
    -n integrador-topdesk \
    -o jsonpath='{.data.API_BASIC_USER}' |
  base64 -d
)"
```

Carregar temporariamente a senha:

```bash
BASIC_PASSWORD="$(
  kubectl get secret integrador-topdesk-secret \
    -n integrador-topdesk \
    -o jsonpath='{.data.API_BASIC_PASSWORD}' |
  base64 -d
)"
```

Executar o teste:

```bash
curl -sS \
  -u "${BASIC_USER}:${BASIC_PASSWORD}" \
  https://api.proativetec.com.br/topdesk/api/v1.0/tasks/ticket/TESTE \
  -w '\nHTTP_STATUS=%{http_code}\n'
```

Remover as variáveis:

```bash
unset BASIC_USER
unset BASIC_PASSWORD
```

---

## 15. Verificar os logs

```bash
kubectl logs \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  --prefix \
  --tail=200
```

---

## 16. Atualizar o GitHub sem enviar os valores

Podem ser versionados:

```text
.gitignore
secret.env.example
README.md
```

Não podem ser versionados:

```text
secret.env
secret-backup.yaml
arquivos contendo senhas reais
```

Verificar:

```bash
git status
```

Adicionar apenas arquivos permitidos:

```bash
git add \
  .gitignore \
  secret.env.example \
  README.md
```

Criar o commit:

```bash
git commit \
  -m "docs: atualiza procedimento e modelo de Secret"
```

Publicar:

```bash
git push origin main
```

---

# Resumo dos Procedimentos de Atualização

| Tipo de alteração | Docker Build | Push ECR | `kubectl apply` | Restart dos Pods |
|---|---:|---:|---|---:|
| Código Python | Sim | Sim | `deployment.yaml` | Automático pelo Rolling Update |
| ConfigMap | Não | Não | `configmap.yaml` | Sim |
| Secret | Não | Não | Secret gerado por `secret.env` | Sim |
| Número de réplicas | Não | Não | `deployment.yaml` ou `kubectl scale` | Não |
| Ingress | Não | Não | `ingress.yaml` | Não |
| Service | Não | Não | `service.yaml` | Normalmente não |

Fluxo de alteração do código:

```text
Alterar código
    ↓
Validar sintaxe
    ↓
Docker build
    ↓
Docker tag
    ↓
Docker push
    ↓
Atualizar deployment.yaml
    ↓
kubectl apply
    ↓
Rolling Update
    ↓
Testes
    ↓
Git commit e push
```

Fluxo de alteração do ConfigMap:

```text
Alterar configmap.yaml
    ↓
kubectl apply
    ↓
kubectl rollout restart
    ↓
Testes
    ↓
Git commit e push
```

Fluxo de alteração do Secret:

```text
Alterar secret.env local
    ↓
Atualizar Secret no Kubernetes
    ↓
kubectl rollout restart
    ↓
Testes
    ↓
Atualizar somente documentação e modelo no Git
```

---

# Reiniciando uma Aplicação

Nunca remover Pods manualmente como procedimento normal de reinicialização.

Utilizar:

```bash
kubectl rollout restart \
  deployment/integrador-topdesk \
  -n integrador-topdesk
```

Acompanhar:

```bash
kubectl rollout status \
  deployment/integrador-topdesk \
  -n integrador-topdesk
```

---

# Aumentando Réplicas

Exemplo:

```bash
kubectl scale deployment \
  integrador-topdesk \
  --replicas=4 \
  -n integrador-topdesk
```

Verificar:

```bash
kubectl get pods \
  -n integrador-topdesk \
  -o wide
```

Após uma alteração manual de escala, atualizar também o campo `replicas` do `deployment.yaml`, para que o GitHub permaneça sincronizado com o ambiente.

---

# Reduzindo Réplicas

```bash
kubectl scale deployment \
  integrador-topdesk \
  --replicas=2 \
  -n integrador-topdesk
```

Confirmar:

```bash
kubectl get deployment integrador-topdesk \
  -n integrador-topdesk
```

---

# Colocando uma Aplicação em Manutenção

Escalar para zero:

```bash
kubectl scale deployment \
  integrador-topdesk \
  --replicas=0 \
  -n integrador-topdesk
```

Confirmar:

```bash
kubectl get deployment integrador-topdesk \
  -n integrador-topdesk
```

Restaurar:

```bash
kubectl scale deployment \
  integrador-topdesk \
  --replicas=2 \
  -n integrador-topdesk
```

Acompanhar a criação dos Pods:

```bash
kubectl get pods \
  -n integrador-topdesk \
  -w
```

---

# Verificando uma Nova Versão

Imagem configurada no Deployment:

```bash
kubectl get deployment integrador-topdesk \
  -n integrador-topdesk \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Imagem utilizada por cada Pod:

```bash
kubectl get pods \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.spec.containers[0].image}{"\n"}{end}'
```

---

# Rollback

Consultar o histórico:

```bash
kubectl rollout history \
  deployment/integrador-topdesk \
  -n integrador-topdesk
```

Executar rollback para a versão anterior:

```bash
kubectl rollout undo \
  deployment/integrador-topdesk \
  -n integrador-topdesk
```

Acompanhar:

```bash
kubectl rollout status \
  deployment/integrador-topdesk \
  -n integrador-topdesk \
  --timeout=180s
```

Confirmar a imagem restaurada:

```bash
kubectl get deployment integrador-topdesk \
  -n integrador-topdesk \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Depois do rollback, atualizar o `deployment.yaml` no GitHub para representar a versão que voltou a ser utilizada em produção.

---

# Situações de Incidente

## Pod reiniciando

Listar os Pods:

```bash
kubectl get pods \
  -n integrador-topdesk
```

Ver os logs:

```bash
kubectl logs \
  <NOME_DO_POD> \
  -n integrador-topdesk
```

Caso o container já tenha reiniciado:

```bash
kubectl logs \
  <NOME_DO_POD> \
  -n integrador-topdesk \
  --previous
```

Depois:

```bash
kubectl describe pod \
  <NOME_DO_POD> \
  -n integrador-topdesk
```

---

## Deployment indisponível

Verificar:

```text
Deployment

↓

ReplicaSet

↓

Pods
```

Comandos:

```bash
kubectl get deployment \
  -n integrador-topdesk
```

```bash
kubectl get replicaset \
  -n integrador-topdesk
```

```bash
kubectl get pods \
  -n integrador-topdesk
```

```bash
kubectl get events \
  -n integrador-topdesk \
  --sort-by='.lastTimestamp'
```

---

## Aplicação indisponível

Fluxo recomendado:

```text
DNS

↓

NLB

↓

NGINX

↓

Ingress

↓

Service

↓

EndpointSlice

↓

Pod

↓

Logs
```

Verificar o DNS:

```bash
dig api.proativetec.com.br
```

Verificar o NLB:

```bash
aws elbv2 describe-load-balancers \
  --region us-east-1
```

Verificar o NGINX:

```bash
kubectl get pods \
  -n ingress-nginx
```

Verificar o Ingress:

```bash
kubectl describe ingress \
  integrador-topdesk \
  -n integrador-topdesk
```

Verificar o Service:

```bash
kubectl describe service \
  integrador-topdesk \
  -n integrador-topdesk
```

Verificar o EndpointSlice:

```bash
kubectl get endpointslice \
  -n integrador-topdesk \
  -l kubernetes.io/service-name=integrador-topdesk \
  -o wide
```

Verificar os Pods:

```bash
kubectl get pods \
  -n integrador-topdesk \
  -o wide
```

Verificar os logs:

```bash
kubectl logs \
  -n integrador-topdesk \
  -l app=integrador-topdesk \
  --prefix \
  --tail=200
```

---

## Banco indisponível

Verificar:

```bash
kubectl get pods \
  -n mariadb
```

Depois:

```bash
kubectl logs mariadb-0 \
  -n mariadb
```

Verificar o Service:

```bash
kubectl get svc \
  -n mariadb
```

Testar a resolução DNS a partir do integrador:

```bash
kubectl exec \
  -n integrador-topdesk \
  deployment/integrador-topdesk \
  -- getent hosts mariadb.mariadb.svc.cluster.local
```

Testar a porta TCP usando Python dentro do Pod:

```bash
kubectl exec \
  -n integrador-topdesk \
  deployment/integrador-topdesk \
  -- python3 -c '
import socket

host = "mariadb.mariadb.svc.cluster.local"
port = 3306

with socket.create_connection((host, port), timeout=5):
    print(f"Conexão TCP com {host}:{port} realizada com sucesso")
'
```

---

# Comandos mais utilizados

```bash
kubectl get nodes

kubectl get pods -A

kubectl get deployment -A

kubectl get replicaset -A

kubectl get svc -A

kubectl get ingress -A

kubectl get endpointslice -A

kubectl logs

kubectl describe

kubectl rollout status

kubectl rollout history

kubectl rollout restart

kubectl rollout undo

kubectl exec -it -- sh

kubectl top nodes

kubectl top pods -A

kubectl get events -A

kubectl apply -f

kubectl diff -f
```

---

# Boas Práticas Operacionais

✔ Nunca editar recursos diretamente em produção sem versionamento.

✔ Nunca utilizar a Tag `latest`.

✔ Nunca reutilizar uma Tag Docker já publicada.

✔ Nunca alterar um Deployment sem atualizar o GitHub.

✔ Sempre validar a sintaxe Python antes do Docker Build.

✔ Sempre validar os manifests com `--dry-run=server`.

✔ Sempre verificar o resultado do `kubectl diff`.

✔ Sempre validar a nova imagem antes do Deployment.

✔ Sempre acompanhar o Rollout.

✔ Sempre verificar os Logs após uma atualização.

✔ Sempre verificar os EndpointSlices após um Deployment.

✔ Sempre testar o Health Check.

✔ Sempre documentar alterações de infraestrutura.

✔ Manter ConfigMaps versionados no GitHub.

✔ Versionar somente modelos de Secret, nunca os valores reais.

✔ Nunca armazenar senhas no GitHub.

✔ Remover credenciais temporárias das variáveis do shell.

✔ Executar backups periódicos do MariaDB.

✔ Manter o GitHub sincronizado com o estado desejado da produção.

---

# Plano de Recuperação

Em caso de incidente crítico:

1. Identificar o componente afetado.
2. Registrar a data e o horário do incidente.
3. Verificar os Events do Kubernetes.
4. Verificar os Logs.
5. Confirmar a versão implantada.
6. Verificar a última alteração realizada.
7. Preservar evidências e Logs relevantes.
8. Executar Rollback, se necessário.
9. Validar o Deployment.
10. Validar os Pods.
11. Validar o EndpointSlice.
12. Validar o Health Check.
13. Validar a operação funcional.
14. Registrar a causa raiz.
15. Atualizar a documentação.
16. Corrigir o manifesto no GitHub para que represente o estado final da produção.---

# 29. Backup e Recuperação de Desastres (Backup & Disaster Recovery)

**Versão:** 1.0

---

# Objetivo

Este documento descreve a estratégia oficial de Backup e Disaster Recovery (DR) da plataforma de Integradores executada no Amazon EKS.

O objetivo é garantir que qualquer componente da solução possa ser restaurado em caso de falha, perda de dados ou indisponibilidade da infraestrutura.

---

# Componentes da Plataforma

A solução é composta pelos seguintes componentes.

```
GitHub

↓

Amazon ECR

↓

Amazon EKS

↓

ConfigMaps

↓

Secrets

↓

MariaDB

↓

Registro.br

↓

Certificados TLS
```

Todos esses componentes devem possuir uma estratégia de backup.

---

# Classificação dos Componentes

| Componente | Backup Necessário |
|------------|------------------|
| GitHub | Sim |
| Docker Images | Sim |
| Amazon ECR | Sim |
| Kubernetes Manifests | Sim |
| ConfigMap | Sim |
| Secret | Sim |
| MariaDB | Sim |
| Certificados TLS | Sim |
| Registro.br | Documentação |

---

# O que NÃO precisa de Backup

Não é necessário realizar backup dos Pods.

Também não é necessário realizar backup dos Deployments em execução.

Esses recursos podem ser recriados automaticamente a partir dos manifests armazenados no GitHub.

---

# Estratégia Geral

A recuperação completa da plataforma depende de quatro pilares.

```
Código

↓

GitHub
```

```
Imagens

↓

Amazon ECR
```

```
Infraestrutura

↓

Manifests Kubernetes
```

```
Dados

↓

MariaDB
```

---

# Backup do GitHub

Todo o código-fonte deve permanecer versionado.

Incluindo:

```
Dockerfile

requirements.txt

deployment.yaml

service.yaml

ingress.yaml

configmap.yaml

README.md

documentação

código Python
```

Nunca armazenar apenas no servidor Linux.

---

# Backup do Amazon ECR

O Amazon ECR armazena todas as versões das imagens Docker.

Exemplo.

```
0.1.0

0.1.1

0.1.2

0.1.3

0.1.4
```

Recomendação.

Nunca remover versões que possam ser necessárias para rollback.

---

# Backup dos manifests Kubernetes

Todos os manifests devem permanecer versionados.

```
deployment.yaml

service.yaml

ingress.yaml

configmap.yaml

secret.example.yaml
```

Em caso de perda completa do Cluster.

Basta executar.

```bash
kubectl apply -f .
```

---

# Backup do ConfigMap

Exportar.

```bash
kubectl get configmap \
integrador-topdesk-config \
-n integrador-topdesk \
-o yaml \
> configmap-backup.yaml
```

---

# Backup do Secret

Exportar.

```bash
kubectl get secret \
integrador-topdesk-secret \
-n integrador-topdesk \
-o yaml \
> secret-backup.yaml
```

**Importante:**

Esses arquivos contêm informações sensíveis.

Devem permanecer criptografados e armazenados em local seguro.

---

# Backup do MariaDB

O banco de dados representa o componente mais crítico da plataforma.

Backup lógico.

```bash
mysqldump \
-u root \
-p \
--single-transaction \
--routines \
--triggers \
--events \
integrador_topdesk \
> integrador_topdesk.sql
```

Recomendação.

Executar diariamente.

---

# Backup Automatizado

Sugestão.

```
02:00

↓

mysqldump

↓

Compressão

↓

Upload para Amazon S3
```

Fluxo.

```
MariaDB

↓

mysqldump

↓

gzip

↓

Amazon S3
```

---

# Backup do Registro.br

Não existe backup propriamente dito.

O importante é documentar.

```
api.proativetec.com.br

↓

CNAME

↓

k8s-ingressn-ingressn-...

```

Essa informação deve constar na documentação operacional.

---

# Backup dos Certificados TLS

Exportar os certificados.

Guardar:

- certificado;
- chave privada;
- cadeia intermediária.

Também manter uma cópia do Secret Kubernetes correspondente.

---

# RPO

Recovery Point Objective.

Define quanto de informação pode ser perdida.

Recomendação.

```
24 horas
```

Ou.

```
4 horas
```

dependendo da criticidade do ambiente.

---

# RTO

Recovery Time Objective.

Define quanto tempo a plataforma pode permanecer indisponível.

Objetivo recomendado.

```
Menor que 2 horas
```

---

# Recuperação Completa

Suponha perda total do Cluster.

Fluxo recomendado.

```
Criar novo Cluster EKS

↓

Instalar NGINX Ingress Controller

↓

Criar Namespace

↓

Criar Secrets

↓

Criar ConfigMaps

↓

Aplicar Deployment

↓

Aplicar Services

↓

Aplicar Ingress

↓

Restaurar MariaDB

↓

Validar aplicação
```

---

# Recuperando apenas o Banco

Criar banco.

```sql
CREATE DATABASE integrador_topdesk;
```

Restaurar.

```bash
mysql \
-u root \
-p \
integrador_topdesk \
< integrador_topdesk.sql
```

---

# Recuperando apenas uma Aplicação

```
GitHub

↓

Clone

↓

Docker Build

↓

Docker Push

↓

kubectl apply

↓

Rollout

↓

Aplicação disponível
```

---

# Disaster Recovery

Para ambientes críticos recomenda-se.

```
Região Primária

↓

Amazon EKS

↓

Amazon S3
```

↓

Replicação.

↓

```
Região Secundária

↓

Amazon EKS

↓

Amazon ECR

↓

Amazon S3
```

Em caso de desastre.

Atualizar apenas o DNS.

---

# Testes de Recuperação

O plano de backup somente é válido quando testado.

Recomenda-se.

- teste mensal de restauração do MariaDB;
- teste trimestral de recuperação da aplicação;
- teste semestral de recuperação completa da plataforma.

---

# Checklist de Backup

Diariamente.

- [ ] Backup do MariaDB
- [ ] Verificação do resultado
- [ ] Upload para S3

Semanalmente.

- [ ] Verificar integridade dos backups
- [ ] Teste de restauração

Mensalmente.

- [ ] Simulação de recuperação completa

---

# Boas Práticas

✔ Manter pelo menos três cópias dos backups.

✔ Armazenar backups em local diferente do Cluster.

✔ Nunca manter apenas backups locais.

✔ Criptografar backups contendo Secrets.

✔ Testar periodicamente a restauração.

✔ Documentar todos os procedimentos.

✔ Versionar todos os manifests no GitHub.

✔ Manter múltiplas versões das imagens no Amazon ECR.

---

# Resumo

A estratégia de Backup e Disaster Recovery da plataforma baseia-se em quatro pilares:

- Código (GitHub)
- Imagens (Amazon ECR)
- Infraestrutura (Kubernetes)
- Dados (MariaDB)

Seguindo este procedimento é possível reconstruir integralmente a plataforma em caso de perda parcial ou total da infraestrutura, garantindo continuidade operacional e reduzindo significativamente o tempo de indisponibilidade.

---

# 30. Segurança da Plataforma

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve a estratégia de segurança adotada na plataforma de Integradores da Proative executada no Amazon EKS.

O objetivo é garantir:

- confidencialidade;
- integridade;
- disponibilidade;
- rastreabilidade;
- menor superfície de ataque.

As recomendações apresentadas deverão ser adotadas por todos os integradores da plataforma.

---

# Arquitetura de Segurança

A segurança da plataforma é composta por diversas camadas independentes.

```
Internet
    │
    ▼
Registro.br
    │
    ▼
AWS Network Load Balancer
    │
    ▼
Security Groups
    │
    ▼
NGINX Ingress Controller
    │
    ▼
Amazon EKS
    │
    ▼
Namespaces
    │
    ▼
Deployments
    │
    ▼
Pods
    │
    ▼
Containers
    │
    ▼
Aplicação
    │
    ▼
MariaDB
```

Mesmo que uma camada seja comprometida, as demais continuam protegendo a plataforma.

---

# Modelo de Segurança

A plataforma utiliza o princípio de **Defesa em Profundidade (Defense in Depth)**.

Isso significa que não existe um único mecanismo responsável pela segurança.

Diversos mecanismos trabalham em conjunto.

Exemplo.

```
TLS

↓

NLB

↓

Security Group

↓

NGINX

↓

Ingress

↓

Service

↓

Pod

↓

Aplicação

↓

Banco
```

---

# Segurança na AWS

A AWS fornece diversos mecanismos de proteção.

Entre eles.

- IAM
- Security Groups
- VPC
- Subnets privadas
- Amazon ECR
- Amazon EKS
- TLS

---

# IAM

Todos os acessos à AWS devem ocorrer através do IAM.

Nunca utilizar a conta Root.

Recomendações.

✔ Usuários individuais.

✔ MFA obrigatório.

✔ Menor privilégio possível.

✔ Rotação periódica das Access Keys.

---

# VPC

Todo o Cluster encontra-se isolado em uma Amazon VPC.

Benefícios.

- isolamento de rede;
- controle de roteamento;
- integração com Security Groups;
- integração com NACL.

---

# Security Groups

Os Security Groups funcionam como Firewall.

Exemplo.

```
Internet

↓

443

↓

NLB

↓

80/443

↓

NGINX
```

Somente portas necessárias devem permanecer abertas.

---

# NACL

As Network ACLs complementam os Security Groups.

Enquanto o Security Group protege instâncias.

A NACL protege Subnets.

---

# Segurança do Amazon EKS

O Control Plane é totalmente administrado pela AWS.

Isso reduz significativamente os riscos relacionados à administração do Kubernetes.

O acesso ocorre apenas através da API Kubernetes.

---

# Namespaces

Cada integrador possui um Namespace exclusivo.

Exemplo.

```
integrador-topdesk

integrador-hpe-suzano

mariadb

ingress-nginx
```

Essa separação reduz o impacto de configurações incorretas.

---

# RBAC

O Kubernetes utiliza RBAC (Role Based Access Control).

Através dele é possível definir.

- quem pode visualizar recursos;
- quem pode alterá-los;
- quem pode removê-los.

Sempre conceder apenas as permissões necessárias.

---

# Segurança dos Containers

Cada Pod executa um único container.

Recomendações.

✔ utilizar imagens oficiais;

✔ remover ferramentas desnecessárias;

✔ minimizar o tamanho da imagem;

✔ executar processos sem privilégios administrativos quando possível.

---

# Amazon ECR

O Amazon ECR armazena todas as imagens Docker.

Boas práticas.

- nunca reutilizar Tags;
- manter histórico das versões;
- remover imagens obsoletas periodicamente;
- restringir permissões de Push.

---

# Dockerfile

O Dockerfile deve permanecer simples.

Evitar.

- instalação de compiladores desnecessários;
- ferramentas administrativas;
- utilitários de depuração em produção.

Quanto menor a imagem.

Menor a superfície de ataque.

---

# ConfigMap

O ConfigMap deve conter apenas informações públicas.

Exemplo.

```
APP_NAME

ROOT_PATH

LOG_LEVEL
```

Nunca armazenar:

- senhas;
- tokens;
- certificados;
- Access Keys.

---

# Secret

Todas as informações confidenciais devem permanecer em Secrets.

Exemplo.

```
Senha MariaDB

Token API

Credenciais LDAP

Chaves privadas
```

Nunca armazenar essas informações no GitHub.

---

# GitHub

O repositório GitHub não deve conter.

- senhas;
- certificados;
- arquivos .env;
- Secrets Kubernetes;
- chaves SSH.

Somente arquivos de exemplo.

Exemplo.

```
secret.example.yaml
```

---

# Certificados TLS

Todo acesso externo deve ocorrer utilizando HTTPS.

Os certificados encontram-se armazenados como Secret Kubernetes.

Fluxo.

```
Cliente

↓

TLS

↓

NGINX

↓

Aplicação
```

---

# Gestão de Senhas

Todas as senhas devem obedecer.

- comprimento mínimo;
- alta complexidade;
- rotação periódica;
- armazenamento seguro.

Nunca reutilizar senhas.

---

# MFA

Sempre que disponível.

Habilitar.

```
Multi Factor Authentication
```

Principalmente para.

- AWS
- GitHub

---

# SSH

O acesso SSH aos servidores Linux deve ocorrer.

- utilizando chaves públicas;
- nunca utilizando senhas.

As chaves privadas nunca devem ser compartilhadas.

---

# Logs

Os Logs não devem conter.

- senhas;
- tokens;
- credenciais;
- dados sensíveis.

Caso necessário.

Mascarar informações.

---

# Atualizações

Manter atualizados.

- Linux;
- Docker;
- Kubernetes;
- Python;
- Bibliotecas;
- Gunicorn;
- Flask.

---

# Hardening

Recomendações.

✔ Containers mínimos.

✔ Usuários não privilegiados.

✔ Somente portas necessárias.

✔ Serviços desnecessários desabilitados.

✔ Atualizações periódicas.

---

# Auditoria

Toda alteração em produção deve ser rastreável.

Recomenda-se.

- GitHub;
- Commits;
- Pull Requests;
- Tags;
- Releases.

Nunca alterar arquivos diretamente em produção.

---

# Incidentes

Em caso de incidente.

1. Identificar o componente.
2. Preservar Logs.
3. Registrar horário.
4. Verificar alterações recentes.
5. Executar rollback se necessário.
6. Atualizar documentação.

---

# Checklist de Segurança

Diariamente.

- [ ] Nodes Ready
- [ ] Pods Running
- [ ] Certificados válidos
- [ ] Sem alterações inesperadas

Semanalmente.

- [ ] Revisar usuários IAM
- [ ] Revisar usuários GitHub
- [ ] Revisar imagens Docker
- [ ] Revisar versões implantadas

Mensalmente.

- [ ] Rotação de senhas
- [ ] Revisão de acessos
- [ ] Atualização de documentação
- [ ] Teste de recuperação

---

# Boas Práticas

✔ Nunca utilizar a conta Root da AWS.

✔ Utilizar MFA.

✔ Utilizar RBAC.

✔ Utilizar Namespaces.

✔ Nunca armazenar Secrets no GitHub.

✔ Versionar toda a infraestrutura.

✔ Utilizar HTTPS.

✔ Atualizar periodicamente todas as imagens.

✔ Executar backups regularmente.

✔ Monitorar continuamente a plataforma.

---

# 31. Monitoramento e Observabilidade da Plataforma

**Versão:** 1.0

---

# Objetivo

Este capítulo descreve a estratégia de Monitoramento e Observabilidade adotada para a plataforma de Integradores executada no Amazon EKS.

O objetivo é permitir a identificação rápida de falhas, degradação de desempenho e indisponibilidade dos serviços, reduzindo o tempo de detecção e resolução de incidentes.

---

# Conceitos

Embora muitas vezes utilizados como sinônimos, Monitoramento e Observabilidade possuem objetivos distintos.

## Monitoramento

Responde à pergunta:

> "A aplicação está funcionando?"

Exemplos.

- CPU
- Memória
- Pods Running
- Health Check
- Logs
- Alertas

---

## Observabilidade

Responde à pergunta:

> "Por que a aplicação deixou de funcionar?"

Ela combina.

- Logs
- Métricas
- Eventos
- Rastreamento

permitindo compreender a causa raiz de um problema.

---

# Arquitetura de Monitoramento

```
Aplicação

↓

Health Check

↓

Liveness Probe

↓

Readiness Probe

↓

Kubernetes

↓

Eventos

↓

Logs

↓

Administrador
```

No futuro essa arquitetura poderá ser integrada a soluções como OpenSearch, Prometheus e Grafana.

---

# Componentes Monitorados

Na plataforma atual devem ser monitorados.

| Componente | Monitoramento |
|------------|---------------|
| Worker Nodes | CPU, Memória, Disco |
| Pods | Status, Restart |
| Deployments | Réplicas |
| Services | Endpoints |
| Ingress | Disponibilidade |
| NGINX | Logs |
| MariaDB | Disponibilidade |
| Aplicações | Health Check |
| Amazon ECR | Versão implantada |
| AWS NLB | Disponibilidade |

---

# Health Check

Cada integrador deve disponibilizar um endpoint.

```
/health
```

Exemplo.

```
https://api.proativetec.com.br/topdesk/health
```

Resposta esperada.

```text
OK
```

Esse endpoint deve validar apenas a disponibilidade básica da aplicação.

---

# Liveness Probe

A Liveness Probe responde:

> "A aplicação ainda está viva?"

Exemplo.

```yaml
livenessProbe:

  httpGet:

    path: /health

    port: 8889
```

Caso falhe repetidamente.

```
Kubernetes

↓

Reinicia o Pod
```

---

# Readiness Probe

A Readiness Probe responde:

> "Este Pod já pode receber requisições?"

Enquanto a resposta for negativa.

```
Service

↓

não envia tráfego
```

Isso evita indisponibilidade durante Rolling Updates.

---

# Startup Probe

Embora ainda não utilizada na plataforma, recomenda-se sua adoção para aplicações com inicialização lenta.

Ela evita que a Liveness Probe reinicie o Pod prematuramente.

---

# Monitoramento dos Pods

Listagem.

```bash
kubectl get pods -A
```

Verificar.

- STATUS
- READY
- RESTARTS

Qualquer aumento inesperado de RESTARTS deve ser investigado.

---

# Monitoramento dos Deployments

```bash
kubectl get deployment -A
```

Verificar.

```
READY

2/2
```

Diferenças entre READY e AVAILABLE podem indicar falhas durante Rolling Updates.

---

# Monitoramento dos Nodes

```bash
kubectl get nodes
```

Esperado.

```
STATUS

Ready
```

---

# Utilização de CPU

Caso o Metrics Server esteja instalado.

```bash
kubectl top nodes
```

Monitorar.

- CPU
- Memória

---

# Utilização dos Pods

```bash
kubectl top pods -A
```

Permite identificar aplicações consumindo recursos excessivos.

---

# Logs da Aplicação

Logs do Integrador.

```bash
kubectl logs \
deployment/integrador-topdesk \
-n integrador-topdesk
```

Monitorar.

- Exceptions
- Tracebacks
- Timeouts
- Erros de autenticação

---

# Logs do NGINX

```bash
kubectl logs \
deployment/ingress-nginx-controller \
-n ingress-nginx
```

Úteis para identificar.

- erros HTTP;
- problemas de roteamento;
- falhas de TLS.

---

# Eventos do Kubernetes

```bash
kubectl get events -A
```

Os eventos frequentemente revelam problemas antes mesmo dos Logs.

---

# Monitoramento do MariaDB

Verificar.

```bash
kubectl get pods \
-n mariadb
```

Logs.

```bash
kubectl logs mariadb-0 \
-n mariadb
```

Monitorar.

- reinicializações;
- erros de conexão;
- utilização de disco.

---

# Monitoramento do AWS Network Load Balancer

Verificar.

- disponibilidade;
- Target Groups;
- Health Checks.

Comandos.

```bash
aws elbv2 describe-load-balancers
```

```bash
aws elbv2 describe-target-health \
--target-group-arn <ARN>
```

---

# Monitoramento do Amazon ECR

Confirmar a versão implantada.

```bash
kubectl get deployment \
integrador-topdesk \
-o jsonpath='{.spec.template.spec.containers[0].image}'
```

---

# Métricas Recomendadas

| Métrica | Frequência |
|----------|------------|
| CPU dos Nodes | Contínua |
| Memória dos Nodes | Contínua |
| CPU dos Pods | Contínua |
| Memória dos Pods | Contínua |
| Restart Count | Contínua |
| Espaço em Disco | Diário |
| Disponibilidade do MariaDB | Contínua |
| Health Check | A cada minuto |
| Certificados TLS | Diário |

---

# Alertas Recomendados

Gerar alerta quando.

- Node ficar NotReady.
- Pod entrar em CrashLoopBackOff.
- Pod entrar em ImagePullBackOff.
- Restart Count aumentar continuamente.
- CPU ultrapassar 80%.
- Memória ultrapassar 85%.
- Disco ultrapassar 80%.
- MariaDB indisponível.
- Endpoint `/health` retornar erro.
- Certificado TLS próximo do vencimento.

---

# SLA, SLI e SLO

## SLA (Service Level Agreement)

Compromisso formal de disponibilidade.

Exemplo.

```
99,9%
```

---

## SLI (Service Level Indicator)

Indicadores medidos.

Exemplos.

- Tempo de resposta
- Disponibilidade
- Taxa de erro

---

## SLO (Service Level Objective)

Meta operacional baseada nos indicadores.

Exemplo.

```
95% das requisições respondidas em menos de 500 ms.
```

---

# Dashboards

Embora a plataforma atual utilize principalmente ferramentas nativas do Kubernetes, recomenda-se futuramente a adoção de dashboards consolidados.

Exemplos.

- OpenSearch Dashboards
- Grafana
- Amazon CloudWatch Dashboards

Esses painéis permitem acompanhar a saúde da plataforma em tempo real.

---

# Fluxo de Diagnóstico

```
Health Check

↓

Pods

↓

Deployment

↓

Service

↓

Ingress

↓

NGINX

↓

MariaDB

↓

Logs

↓

Eventos

↓

Aplicação
```

---

# Checklist Diário

- [ ] Todos os Nodes estão Ready.
- [ ] Todos os Pods estão Running.
- [ ] Nenhum Pod em CrashLoopBackOff.
- [ ] Health Check respondendo.
- [ ] MariaDB disponível.
- [ ] NGINX operacional.
- [ ] Sem aumento de Restart Count.
- [ ] CPU abaixo de 80%.
- [ ] Memória abaixo de 85%.

---

# Boas Práticas

✔ Implementar `/health` em todos os integradores.

✔ Configurar Liveness e Readiness Probes.

✔ Monitorar continuamente Restart Count.

✔ Revisar Logs diariamente.

✔ Investigar qualquer aumento inesperado de consumo de recursos.

✔ Configurar alertas automáticos para componentes críticos.

✔ Centralizar logs e métricas quando a plataforma evoluir.

---

# 32. Evolução da Plataforma e Guia para Novos Integradores

**Versão:** 1.0

---

# Objetivo

Este capítulo estabelece o padrão oficial para desenvolvimento, implantação e manutenção de novos integradores da plataforma Proative.

Todos os novos projetos deverão seguir as recomendações aqui descritas, garantindo padronização, facilidade de manutenção, escalabilidade e redução do esforço operacional.

Este documento deve ser considerado a referência oficial para criação de novos integradores.

---

# Filosofia da Plataforma

Todos os integradores devem compartilhar a mesma arquitetura.

```
Cliente

↓

Registro.br

↓

AWS Network Load Balancer

↓

NGINX Ingress Controller

↓

Ingress

↓

Service

↓

Deployment

↓

Pods

↓

Aplicação

↓

Banco de Dados
```

A infraestrutura é compartilhada.

Cada integrador possui apenas seus próprios recursos Kubernetes.

---

# Objetivos da Plataforma

A arquitetura foi construída para atender aos seguintes objetivos.

- simplicidade;
- baixo custo operacional;
- alta disponibilidade;
- escalabilidade horizontal;
- facilidade de implantação;
- facilidade de manutenção;
- padronização entre projetos.

---

# Estrutura Padrão de Diretórios

Todo novo projeto deverá seguir a estrutura abaixo.

```
/opt/proative

└── integrador-nome
    │
    ├── app/
    │
    ├── logs/
    │
    ├── attaches/
    │
    ├── Dockerfile
    ├── .dockerignore
    ├── requirements.txt
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secret.example.yaml
    ├── README.md
    └── .gitignore
```

Essa estrutura deve ser mantida em todos os integradores.

---

# Estrutura da Aplicação

Recomenda-se.

```
app/

├── api/

├── auth/

├── database/

├── models/

├── routes/

├── services/

├── utils/

└── main.py
```

A separação por camadas facilita manutenção e testes.

---

# Docker

Todos os projetos deverão possuir.

```
Dockerfile
```

e

```
.dockerignore
```

Não utilizar Dockerfiles distintos para aplicações semelhantes.

---

# Versionamento

Todos os projetos utilizarão Semantic Versioning.

```
MAJOR.MINOR.PATCH
```

Exemplo.

```
0.1.0

0.1.1

0.2.0

1.0.0
```

A mesma versão deverá aparecer em.

- Git Tag
- Docker Tag
- Amazon ECR
- Deployment

---

# GitHub

Cada projeto deverá possuir um repositório próprio.

Exemplo.

```
integrador-topdesk

integrador-hpe-suzano

integrador-zabbix-opmon

wireair

onevision
```

Todos os repositórios deverão conter documentação completa.

---

# Build

Fluxo oficial.

```
GitHub

↓

git pull

↓

Alteração

↓

Build Docker

↓

Push Amazon ECR

↓

Atualização Deployment

↓

kubectl apply

↓

Rollout

↓

Testes

↓

Git Push
```

Esse fluxo deverá ser seguido por todos os desenvolvedores.

---

# ConfigMap

Toda configuração não sensível deverá permanecer no ConfigMap.

Exemplos.

```
APP_NAME

ROOT_PATH

LOG_LEVEL

DEBUG
```

---

# Secret

Todas as informações confidenciais deverão permanecer em Secret.

Exemplos.

```
Senha MariaDB

Tokens

Credenciais LDAP

Access Keys

Certificados
```

Nunca armazenar essas informações no GitHub.

---

# Banco de Dados

Cada integrador deverá possuir seu próprio banco.

Exemplo.

```
integrador_topdesk

integrador_hpe_suzano

integrador_zabbix_opmon
```

Evitar compartilhamento de tabelas entre aplicações.

---

# Deployment

Cada integrador possuirá.

```
1 Deployment
```

Responsável por.

- Pods;
- Réplicas;
- Rolling Update.

---

# Service

Cada integrador possuirá.

```
1 Service
```

Sempre do tipo.

```
ClusterIP
```

---

# Ingress

Cada integrador possuirá.

```
1 Ingress
```

Exemplo.

```
/topdesk

/hpe-suzano

/zabbix

/wireair
```

Todos compartilhando.

```
api.proativetec.com.br
```

---

# Health Check

Todo projeto deverá disponibilizar.

```
/health
```

Resposta.

```
OK
```

Esse endpoint será utilizado pelas Probes do Kubernetes.

---

# Logs

Todos os integradores deverão registrar.

- inicialização;
- erros;
- autenticação;
- exceções;
- operações importantes.

Evitar registrar dados sensíveis.

---

# Segurança

Todo novo projeto deverá utilizar.

- HTTPS;
- ConfigMap;
- Secret;
- GitHub;
- Docker;
- Amazon ECR;
- Amazon EKS.

Nunca executar aplicações diretamente em máquinas virtuais.

---

# Checklist para Novo Integrador

Antes da implantação verificar.

- [ ] Repositório Git criado.
- [ ] README.md atualizado.
- [ ] Dockerfile criado.
- [ ] requirements.txt revisado.
- [ ] deployment.yaml criado.
- [ ] service.yaml criado.
- [ ] ingress.yaml criado.
- [ ] ConfigMap criado.
- [ ] Secret criado.
- [ ] Banco criado.
- [ ] Build Docker realizado.
- [ ] Push Amazon ECR realizado.
- [ ] Deployment aplicado.
- [ ] Rollout validado.
- [ ] Health Check funcionando.
- [ ] Logs verificados.
- [ ] Documentação concluída.

---

# Evoluções Futuras

A arquitetura foi projetada para permitir crescimento gradual.

Entre as evoluções previstas destacam-se.

---

## Horizontal Pod Autoscaler (HPA)

Escalonamento automático baseado em CPU e Memória.

---

## GitOps

Gerenciamento declarativo utilizando Git como fonte única da verdade.

Ferramentas recomendadas.

- ArgoCD
- FluxCD

---

## CI/CD

Automatização do pipeline.

Fluxo futuro.

```
Commit

↓

GitHub Actions

↓

Docker Build

↓

Amazon ECR

↓

Deploy Automático

↓

Testes

↓

Produção
```

---

## Multiambiente

Separação entre.

```
DEV

HML

PRD
```

Cada ambiente possuirá.

- Namespace;
- ConfigMap;
- Secret;
- Banco.

---

## Disaster Recovery

Implantação de ambiente secundário em outra Região AWS.

Objetivos.

- redução do RTO;
- redução do RPO;
- continuidade operacional.

---

## Observabilidade

Integração futura com.

- OpenSearch
- Prometheus
- Grafana
- Amazon CloudWatch

Permitindo dashboards unificados.

---

## Escalabilidade

A plataforma suporta crescimento horizontal.

Novos integradores exigirão apenas.

```
Deployment

↓

Service

↓

Ingress
```

Sem necessidade de novos Load Balancers.

---

# Padrões Obrigatórios

Todos os novos projetos deverão obrigatoriamente seguir.

✔ Estrutura de diretórios padronizada.

✔ Versionamento SemVer.

✔ GitHub.

✔ Docker.

✔ Amazon ECR.

✔ Amazon EKS.

✔ ConfigMap.

✔ Secret.

✔ Health Check.

✔ README atualizado.

✔ Documentação técnica.

✔ Backup.

✔ Rollback.

✔ Segurança.

---

# Considerações Finais

A arquitetura adotada para a Plataforma Proative foi concebida com foco em simplicidade operacional, padronização e escalabilidade.

A utilização de Kubernetes, Docker, Amazon ECR, Amazon EKS e GitHub permite que novos integradores sejam desenvolvidos de maneira consistente, reduzindo significativamente o tempo de implantação e manutenção.

Este documento estabelece as diretrizes oficiais para evolução da plataforma e deverá ser utilizado como referência para todos os projetos futuros.

O cumprimento desses padrões garante que a plataforma permaneça organizada, segura, rastreável e preparada para crescer de forma sustentável, preservando a qualidade técnica e operacional ao longo do tempo.

