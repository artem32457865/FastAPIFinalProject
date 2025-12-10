import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes import auth_router, frontend_router, user_account_router

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Импортируем шаблоны
templates = Jinja2Templates(directory="templates")

# Подключение роутеров
app.include_router(frontend_router, prefix="", tags=["frontend"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_account_router, prefix="/account", tags=["account"])


# Глобальный обработчик ошибок 404
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 404,
            "error_message": "Сторінка не знайдена"
        },
        status_code=404
    )


# Глобальный обработчик ошибок 500 и других исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_code = 500
    error_message = "Внутрішня помилка сервера"
    
    if isinstance(exc, HTTPException):
        error_code = exc.status_code
        error_message = exc.detail
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": error_code,
            "error_message": str(error_message)
        },
        status_code=error_code
    )


# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 422,
            "error_message": "Некоректні дані запиту"
        },
        status_code=422
    )


# Обработчик ошибок 401 (не авторизован)
@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 401,
            "error_message": "Необхідно авторизуватися"
        },
        status_code=401
    )


# Обработчик ошибок 403 (запрещено)
@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 403,
            "error_message": "Доступ заборонено"
        },
        status_code=403
    )


# Тестовый роут для проверки ошибки 500
@app.get("/test-error-500")
async def test_error_500():
    raise Exception("Тестова помилка сервера")


# Тестовый роут для проверки ошибки 404
@app.get("/test-error-404")
async def test_error_404():
    raise HTTPException(status_code=404, detail="Тестова сторінка не знайдена")


# Тестовый роут для проверки ошибки 401
@app.get("/test-error-401")
async def test_error_401():
    raise HTTPException(status_code=401, detail="Тестова помилка авторизації")


# Тестовый роут для проверки ошибки 403
@app.get("/test-error-403")
async def test_error_403():
    raise HTTPException(status_code=403, detail="Тестова помилка доступу")


# Основной роут для проверки работоспособности
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Сервер працює нормально"}


# Главная страница API
@app.get("/api")
async def api_root():
    return {
        "message": "RepairHub API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "account": "/account",
            "frontend": "/"
        }
    }


if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", port=8000, reload=True)