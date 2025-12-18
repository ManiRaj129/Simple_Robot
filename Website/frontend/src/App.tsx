import { BrowserRouter, Route, Routes} from 'react-router-dom'
import Home from "./components/Home"
import Interaction from "./components/Interaction"
import Login from "./components/Login"
import { ToastContainer } from 'react-toastify'

function App() {

  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route index element={<Home />} />
          <Route path='/home' element={<Home />} />
          <Route path='/interaction' element={<Interaction />} />
          <Route path='/login' element={<Login/>} />
        </Routes>
        <ToastContainer
          position='bottom-right'
          autoClose={3000}
          hideProgressBar={true}
          closeOnClick={true}
        />
      </BrowserRouter>
    </>
  )
}
export default App;