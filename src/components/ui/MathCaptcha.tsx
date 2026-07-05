import { useState, useCallback } from 'react';

function generateNumbers() {
  const a = Math.floor(Math.random() * 9) + 1;
  const b = Math.floor(Math.random() * 9) + 1;
  return { a, b };
}

interface MathCaptchaProps {
  onValidChange: (valid: boolean) => void;
  showError?: boolean;
}

export function MathCaptcha({ onValidChange, showError }: MathCaptchaProps) {
  const [nums, setNums] = useState(generateNumbers);
  const [value, setValue] = useState('');
  const [touched, setTouched] = useState(false);

  const isValid = value !== '' && parseInt(value, 10) === nums.a + nums.b;
  const showValidationError = (touched || showError) && !isValid;
  const errorMessage = value === '' ? 'Este campo es requerido' : 'Respuesta incorrecta';

  const refresh = useCallback(() => {
    setNums(generateNumbers());
    setValue('');
    setTouched(false);
    onValidChange(false);
  }, [onValidChange]);

  const handleChange = (val: string) => {
    setValue(val);
    setTouched(true);
    const num = parseInt(val, 10);
    onValidChange(val !== '' && !isNaN(num) && num === nums.a + nums.b);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-semibold text-quien-charcoal">
        {`Verificación: ¿Cuánto es ${nums.a} + ${nums.b}?`}
      </label>
      <div className="flex gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Escribe el resultado"
          className="input flex-1 rounded-2xl border-quien-border bg-white text-quien-charcoal focus:border-quien-green focus:outline-none"
        />
        <button
          type="button"
          onClick={refresh}
          title="Nueva pregunta"
          className="btn btn-square btn-ghost btn-sm text-quien-charcoal/60"
          aria-label="Nueva pregunta"
        >
          ↻
        </button>
      </div>
      {showValidationError && (
        <span className="text-xs text-quien-coral">{errorMessage}</span>
      )}
    </div>
  );
}
