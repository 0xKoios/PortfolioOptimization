FROM python:3.11.1-buster
WORKDIR /app
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install -U pip wheel cmake
RUN pip install pybind11
RUN pip install cvxpy
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "main.py"]