/**
 * Uruguayan departments and their localities.
 * Used by the SearchPanel component for the department → locality
 * dependent select behavior.
 *
 * This is mock data — easy to replace later with an API response.
 */
export const uruguayLocations: Record<string, string[]> = {
  Artigas: ['Artigas', 'Bella Unión', 'Tomás Gomensoro'],
  Canelones: ['Canelones', 'Las Piedras', 'Pando', 'Ciudad de la Costa', 'Santa Lucía', 'Atlántida'],
  'Cerro Largo': ['Melo', 'Río Branco', 'Fraile Muerto'],
  Colonia: ['Colonia del Sacramento', 'Carmelo', 'Juan Lacaze', 'Nueva Helvecia'],
  Durazno: ['Durazno', 'Sarandí del Yí', 'Villa del Carmen'],
  Flores: ['Trinidad', 'Ismael Cortinas'],
  Florida: ['Florida', 'Sarandí Grande', 'Casupá'],
  Lavalleja: ['Minas', 'José Pedro Varela', 'Solís de Mataojo', 'Mariscala', 'José Batlle y Ordóñez', 'Zapicán', 'Pirarajá'],
  Maldonado: ['Maldonado', 'Punta del Este', 'San Carlos', 'Piriápolis', 'Pan de Azúcar'],
  Montevideo: ['Montevideo'],
  Paysandú: ['Paysandú', 'Guichón', 'Quebracho'],
  'Río Negro': ['Fray Bentos', 'Young', 'Nuevo Berlín'],
  Rivera: ['Rivera', 'Tranqueras', 'Vichadero'],
  Rocha: ['Rocha', 'Chuy', 'La Paloma', 'Castillos', 'Lascano'],
  Salto: ['Salto', 'Constitución', 'Belén'],
  'San José': ['San José de Mayo', 'Libertad', 'Ciudad del Plata'],
  Soriano: ['Mercedes', 'Dolores', 'Cardona'],
  Tacuarembó: ['Tacuarembó', 'Paso de los Toros', 'San Gregorio de Polanco'],
  'Treinta y Tres': ['Treinta y Tres', 'Vergara', 'Santa Clara de Olimar'],
};

export const departmentList = Object.keys(uruguayLocations).sort();