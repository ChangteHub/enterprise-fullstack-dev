import { createBrowserRouter } from 'react-router-dom';
import StudentList from '../pages/StudentList';

export const router = createBrowserRouter([{ path: '/', element: <StudentList /> }]);
