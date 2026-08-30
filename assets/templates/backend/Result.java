package com.example.common;

/**
 * 统一响应包装 Result<T>。所有 Controller 返回值均使用此结构，
 * 与全局异常处理器配合：正常 -> Result.ok(data)，业务失败 -> 抛 BusinessException 转标准错误 JSON。
 */
public class Result<T> {

    private int code;       // 0 成功；非 0 为业务/系统错误码，与 HTTP 状态码配合使用
    private String message;
    private T data;

    private Result(int code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> Result<T> ok(T data) {
        return new Result<>(0, "ok", data);
    }

    public static <T> Result<T> ok(String message, T data) {
        return new Result<>(0, message, data);
    }

    public static <T> Result<T> fail(int code, String message) {
        return new Result<>(code, message, null);
    }

    public int getCode() { return code; }
    public String getMessage() { return message; }
    public T getData() { return data; }
}
