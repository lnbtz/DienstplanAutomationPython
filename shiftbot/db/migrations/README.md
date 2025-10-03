Generic single-database configuration.
alembic revision --autogenerate -m "put you table create / change message here"
alembic upgrade head
docker exec -it <DOCKER NAME> psql -U <DB USER> -d <DB NAME> -c "\dt"