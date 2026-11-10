FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

COPY handler.py ./

CMD ["handler.lambda_handler"]
