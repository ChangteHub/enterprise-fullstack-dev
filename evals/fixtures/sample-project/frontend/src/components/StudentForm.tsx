import { useState } from 'react';
import { createStudent } from '../services/student';

export default function StudentForm({ onSaved }: { onSaved: () => void }) {
  const [name, setName] = useState('');

  return (
    <form onSubmit={async (e) => { e.preventDefault(); await createStudent({ name }); setName(''); onSaved(); }}>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="姓名" />
      <button type="submit">保存</button>
    </form>
  );
}
