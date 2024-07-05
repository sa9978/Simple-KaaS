FROM python:3.9.19-alpine

WORKDIR /app

COPY  requirements.txt /app/
RUN pip install -r requirements.txt

COPY app.py get_deployment_info_service.py create_application_service.py create_predefined.py /app/

# RUN pip freeze > requirements.txt

CMD [ "python", "app.py"]