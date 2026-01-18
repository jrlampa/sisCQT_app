import React, { useState } from 'react';
import ProjetoList from './components/ProjetoList';
import ConfigurationPage from './components/ConfigurationPage';
import './App.css';

function App() {
  const [page, setPage] = useState<'projetos' | 'configuracoes'>('projetos');

  return (
    <div className="App">
      <header className="App-header">
        <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
          <div className="container-fluid">
            <a className="navbar-brand" href="#">SisCQT React Frontend</a>
            <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
              <span className="navbar-toggler-icon"></span>
            </button>
            <div className="collapse navbar-collapse" id="navbarNav">
              <ul className="navbar-nav">
                <li className="nav-item">
                  <a className={`nav-link ${page === 'projetos' ? 'active' : ''}`} href="#" onClick={() => setPage('projetos')}>
                    Projetos
                  </a>
                </li>
                <li className="nav-item">
                  <a className={`nav-link ${page === 'configuracoes' ? 'active' : ''}`} href="#" onClick={() => setPage('configuracoes')}>
                    Configurações
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </nav>
      </header>
      <main>
        {page === 'projetos' && <ProjetoList />}
        {page === 'configuracoes' && <ConfigurationPage />}
      </main>
    </div>
  );
}

export default App;
