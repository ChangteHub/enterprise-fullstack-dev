import { useEffect, useState } from 'react';
import { listStudents, deleteStudent } from '../services/student';
import type { Student } from '../services/student';
import StudentForm from '../components/StudentForm';

export default function StudentList() {
  const [items, setItems] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await listStudents();
      setItems(res.data.data ?? []);
    } catch {
      setError('加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const remove = async (id: number) => {
    await deleteStudent(id);
    void load();
  };

  return (
    <div>
      {loading && <p>加载中...</p>}
      {error && <p role="alert">{error}</p>}
      <ul>{items.map((s) => <li key={s.id}>{s.name}<button onClick={() => remove(s.id)}>删除</button></li>)}</ul>
      <StudentForm onSaved={load} />
    </div>
  );
}
