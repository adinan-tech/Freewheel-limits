FROM container-registry.oracle.com/oci_functions/python:3.12-dev AS build

WORKDIR /function
COPY function/requirements.txt /function/requirements.txt
RUN pip3 install --target /python --no-cache-dir -r /function/requirements.txt
COPY limit_checker /function/limit_checker
COPY function/func.py /function/func.py

FROM container-registry.oracle.com/oci_functions/python:3.12
WORKDIR /function
COPY --from=build /python /python
COPY --from=build /function /function
ENV PYTHONPATH=/function:/python
ENTRYPOINT ["/python/bin/fdk", "/function/func.py", "handler"]
