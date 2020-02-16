FROM python:3.7-alpine3.10
EXPOSE 5000
ENV PYTHONUNBUFFERED 1
RUN mkdir /server
WORKDIR /server
COPY . /server/
ENTRYPOINT [ "python", "app.py" ]
