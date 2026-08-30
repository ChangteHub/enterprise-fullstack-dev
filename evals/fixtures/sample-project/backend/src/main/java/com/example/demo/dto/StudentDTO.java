package com.example.demo.dto;

import jakarta.validation.constraints.NotBlank;

public class StudentDTO {
    private Long id;

    @NotBlank
    private String name;

    public Long getId() { return id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
