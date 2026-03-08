import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Modules from './pages/Modules';
import ModuleDetail from './pages/ModuleDetail';
import BuildGuide from './pages/BuildGuide';
import RepairGuide from './pages/RepairGuide';
import Specs from './pages/Specs';
import Store from './pages/Store';
import About from './pages/About';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/modules" element={<Modules />} />
        <Route path="/modules/:id" element={<ModuleDetail />} />
        <Route path="/build" element={<BuildGuide />} />
        <Route path="/repair" element={<RepairGuide />} />
        <Route path="/specs" element={<Specs />} />
        <Route path="/store" element={<Store />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </Layout>
  );
}
