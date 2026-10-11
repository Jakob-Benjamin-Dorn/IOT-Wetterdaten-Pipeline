-- Legt den Lese-Benutzer für Grafana an (idempotent, kann beliebig oft laufen).
-- Grafana braucht nur SELECT und soll nie mit dem RDS-Master-Benutzer arbeiten.
--
-- Aufruf als Master-Benutzer (Zugangsdaten stehen in Secrets Manager):
--   psql "host=<rds-endpoint> dbname=weather user=<master> sslmode=require" \
--     -v grafana_user=grafana_reader \
--     -v grafana_password="$(aws ssm get-parameter --name <grafana-db-password-parameter> \
--          --with-decryption --query Parameter.Value --output text)" \
--     -f database/grafana_reader.sql
--
-- Das Passwort sollte nur aus Buchstaben und Ziffern bestehen
-- (z. B. `openssl rand -hex 24`), weil Grafana es in die Datasource-YAML einsetzt.

\set ON_ERROR_STOP on

SELECT format('CREATE ROLE %I LOGIN', :'grafana_user')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'grafana_user')
\gexec

SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'grafana_user', :'grafana_password')
\gexec

-- Zusätzliche Absicherung: Sitzungen dieses Benutzers sind schreibgeschützt.
SELECT format('ALTER ROLE %I SET default_transaction_read_only = on', :'grafana_user')
\gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'grafana_user')
\gexec

SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'grafana_user')
\gexec

SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA public TO %I', :'grafana_user')
\gexec

-- Tabellen, die der Master-Benutzer später anlegt (z. B. per Lambda-Migration).
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT ON TABLES TO %I',
    current_user, :'grafana_user'
)
\gexec
