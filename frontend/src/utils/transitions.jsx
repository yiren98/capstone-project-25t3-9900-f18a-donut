import { SoftSlide } from '../components/PageTransition'; 

export const withTransition = (Comp, ComponentVariant  = SoftSlide) =>
  function Wrapped(props) {
    return (
      <div className="min-h-screen" style={{ perspective: 1000 }}>
        <ComponentVariant >
          <Comp {...props} />
        </ComponentVariant >
      </div>
    );
  };