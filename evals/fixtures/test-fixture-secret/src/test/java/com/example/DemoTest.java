package com.example;

/** 测试 fixture：SECRET 常量应被识别为测试样例值（WARN），不得判 CRITICAL 阻断。 */
public class DemoTest {
    private static final String SECRET = "unit-test-jwt-secret-with-32-bytes!!";
}
