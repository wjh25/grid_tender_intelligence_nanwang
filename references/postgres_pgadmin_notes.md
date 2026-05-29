# PostgreSQL 和 pgAdmin 运维记录

## PostgreSQL Docker

远端主机：

```text
172.16.1.101
```

Docker 镜像源：

```text
https://docker.1ms.run
```

容器：

```text
grid-tender-postgres
```

镜像：

```text
docker.1ms.run/postgres:16
```

数据卷：

```text
grid_tender_postgres_data
```

数据库连接：

```text
database: grid_tender
user: grid_tender
password: <DB_PASSWORD>
```

端口绑定：

```text
127.0.0.1:5432 -> 5432/tcp
```

只绑定远端本机 localhost，避免直接暴露到局域网。

## OpenClaw 服务器本机连接

openclaw 和 PostgreSQL Docker 都在 `172.16.1.101`，所以 skill 运行时不需要 SSH 隧道。

服务器本机连接参数：

```text
host: 127.0.0.1
port: 5432
database: grid_tender
user: grid_tender
password: <DB_PASSWORD>
```

当前代码也可以继续通过容器内 psql 写库：

```bash
docker exec -i grid-tender-postgres psql -U grid_tender -d grid_tender
```

## Mac pgAdmin 可选连接

Mac 不在服务器本机上，所以如果要从 Mac 的 pgAdmin 查看数据库，仍然需要 SSH tunnel，除非以后主动把 Docker 端口改成 LAN 暴露。

Mac 通过 SSH tunnel 访问：

```bash
sshpass -p <SSH_PASSWORD> ssh -f -N -L 15432:127.0.0.1:5432 untu@172.16.1.101
```

pgAdmin server 配置，即走这个 tunnel：

```text
Group: Grid Tender
Name: grid_tender_intelligence_nanwang
Host: 127.0.0.1
Port: 15432
Maintenance DB: grid_tender
Username: grid_tender
PasswordExecCommand: /bin/echo <DB_PASSWORD>
```

pgAdmin 本地配置库：

```text
/Users/wjh/.pgadmin/pgadmin4.db
```

导入过的 server：

```text
Grid Tender / grid_tender_intelligence_nanwang
```

## MySQL 用户理解 PostgreSQL

类比：

```text
MySQL database   ≈ PostgreSQL database
MySQL table      ≈ PostgreSQL table
PostgreSQL schema public ≈ database 下面的一层命名空间
```

当前结构：

```text
PostgreSQL server
└── database: grid_tender
    └── schema: public
        ├── tender_documents
        ├── document_blocks
        ├── tender_requirements
        └── ...
```

常用命令：

```sql
\l                         -- show databases
\c grid_tender             -- use grid_tender
\dn                        -- show schemas
\dt                        -- show tables
\dv                        -- show views
\d tender_documents        -- desc tender_documents
```
