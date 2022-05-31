# front end build environment
FROM python:3 as streamline_web

# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr 
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY streamline_web/requirements.txt /app/
# install pip requirements
RUN python -m pip install -r /app/requirements.txt
RUN pip install python-dotenv

# copy django application
#COPY streamline_web/ /app
# overwrite settings file with prodcution settings file
#COPY streamline_web/streamline_web/settings_production.py /app/streamline_web/settings.py

# application entry point
CMD [ "python", "./manage.py", "runserver", "0.0.0.0:80"] 