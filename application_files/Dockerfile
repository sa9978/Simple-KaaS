FROM python:3.9.19-alpine

WORKDIR /app

COPY app.py get_deployment_info_service.py create_application_service.py requirements.txt /app/

# RUN pip freeze > requirements.txt

RUN pip install -r requirements.txt

CMD [ "python", "app.py"]