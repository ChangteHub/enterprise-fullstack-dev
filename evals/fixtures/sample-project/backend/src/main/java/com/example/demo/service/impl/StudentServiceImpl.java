package com.example.demo.service.impl;

import com.example.demo.dto.StudentDTO;
import com.example.demo.service.StudentService;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class StudentServiceImpl implements StudentService {

    @Override
    public List<StudentDTO> list() {
        return List.of();
    }

    @Override
    public StudentDTO create(StudentDTO dto) {
        return dto;
    }

    @Override
    public void delete(Long id) {
    }
}
