import axios from 'axios';

const http = axios.create({ baseURL: '/api', timeout: 10000 });

export interface Student {
  id: number;
  name: string;
}

export const listStudents = () => http.get('/students');
export const createStudent = (data: Omit<Student, 'id'>) => http.post('/students', data);
export const deleteStudent = (id: number) => http.delete(`/students/${id}`);
