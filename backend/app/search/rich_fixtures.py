"""Fictional providers with practical services and confusable search evidence."""

import hashlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.api.jobkler import normalize, update_search_text
from app.extensions import db
from app.models import Account, Category, Locality, Profile, SeedState
from app.models.jobkler import utcnow

from .catalog import resolve_coverage_values
from .documents import sync_profile_search


SEED_KEY = "jobkler-rich-search-demo-v1"
_CREATED_AT = datetime(2026, 9, 23)
_DESCRIPTION_SUFFIX = " Perfil ficticio de demostración."

# SHA-256 of each previous summary, newline and full published description.
_LEGACY_COPY = {
    "pata-cama-minas": "96fb559cf86f0d0d84e11ef3d34f4a0eb5f1335770fdfe9cfaee639fdec8111e",
    "camas-solis": "e8ac2174032f809c5d53345c207c077afd7b0bb4e96060bb5c7750390868787d",
    "no-camas-minas": "73687ba8c0ba0a6fd4fe5a6cbe0d3ce4c2d4620c8641dd53950bda04a3289f5d",
    "camas-montevideo": "d066441b45c34cd4e7b8d6df57a6f98ede41b4cd1f0e28d0456c1fc551f714e2",
    "camas-inactivo": "0b3cad4bcdef9c19ede22ba88dab0cbc2cb66ddf09f1d35f5403b6a76f4854c0",
    "camas-metalicas-maldonado": "616dc1bb4a38ebcc45872ce0deea2749dbe0ab851eba5fa14a60b19f894b1a84",
    "tapiceria-colonia": "d2cbb44c5c9a93592abd03ef066fd422d195e2a8a8ae995e478b28fa4b09d3fd",
}


@dataclass(frozen=True)
class DemoProfile:
    key: str
    name: str
    category: str
    profession: str
    locality: str
    summary: str
    description: str
    coverage: tuple[str, ...] = ()
    active: bool = True

    @property
    def profile_id(self):
        return f"rich-demo-{self.key}"

    @property
    def owner_id(self):
        return f"rich-demo-owner-{self.key}"


PROFILES = (
    DemoProfile(
        "pata-cama-minas", "Andrea Lago", "oficios", "Carpintería", "minas",
        "Restauración de muebles de madera y ajustes de estructura.",
        "Reparo muebles de madera y sustituyo piezas estructurales cuando se quiebran. "
        "Refuerzo uniones flojas y corrijo apoyos desnivelados en mesas y sillas. "
        "Reviso el estado del resto del mueble antes de cotizar y preparo los repuestos a medida "
        "cuando la pieza original ya no se consigue.",
    ),
    DemoProfile(
        "camas-solis", "Rafael Curbelo", "oficios", "Ebanistería", "solis-de-mataojo",
        "Restauro mobiliario antiguo y repongo piezas de madera.",
        "Reparo muebles de madera que perdieron estabilidad por desgaste de sus uniones. "
        "Rehago espigas y apoyos, sustituyo listones partidos y ajusto ensambles vencidos. "
        "Para muebles antiguos busco una madera y un acabado similares al original. "
        "Coordino recorridas a domicilio para comprobar medidas antes de llevar piezas al taller.",
        ("Minas",),
    ),
    DemoProfile(
        "muebles-minas", "Julia Sanguinetti", "oficios", "Restauración de muebles", "minas",
        "Ajustes y arreglos en muebles domésticos de madera.",
        "Reparo muebles de madera que perdieron firmeza por uso o humedad. "
        "Encolo uniones flojas, cambio tarugos deformados y reconstruyo apoyos o patas quebradas. "
        "También nivelo muebles que quedaron inestables después de una mudanza y recupero el acabado "
        "de cómodas y mesas sin reemplazar herrajes que todavía funcionan.",
    ),
    DemoProfile(
        "no-camas-minas", "Sebastián Lagos", "oficios", "Carpintería", "minas",
        "Reparo sillas y mesas de madera livianas.",
        "Reparo sillas de comedor con patas flojas, apretando o cambiando las uniones que fallan. "
        "También ajusto mesas bajas y arreglo respaldos despegados. "
        "Trabajo exclusivamente con sillas y mesas pequeñas. No arreglo otros muebles ni estructuras pesadas. "
        "Recibo solamente las piezas que se puedan trasladar a mi taller.",
    ),
    DemoProfile(
        "camas-montevideo", "Gabriela Oliver", "oficios", "Restauración de mobiliario", "montevideo",
        "Arreglo de estructuras de madera y ensambles de mobiliario.",
        "Reparo muebles de madera con largueros vencidos o ensambles flojos en Montevideo. "
        "Corrijo puntos de apoyo desnivelados y cambio listones dañados conservando las dimensiones originales. "
        "Hice un trabajo antiguo en Minas y lo menciono como referencia de experiencia. "
        "En la actualidad atiendo únicamente en Montevideo.",
    ),
    DemoProfile(
        "camas-inactivo", "Iván Meyer", "oficios", "Carpintería", "minas",
        "Reparación de mobiliario doméstico de madera.",
        "Reparo muebles de madera con apoyos vencidos, tornillos barridos o un larguero dañado. "
        "Cambio listones y compruebo que la estructura quede firme y nivelada. "
        "También ajusto uniones descuadradas y sustituyo herrajes que ya no aseguran las piezas.",
        active=False,
    ),
    DemoProfile(
        "camas-metalicas-maldonado", "Noelia Acosta", "oficios", "Herrería", "maldonado",
        "Soldadura y ajuste de estructuras domésticas de acero.",
        "Reparo estructuras de muebles metálicos con soldaduras abiertas o tubos de acero deformados. "
        "Puedo sustituir apoyos tubulares y revisar si el bastidor quedó torcido después de un golpe. "
        "También reparo soportes de estanterías y pies de mesas. No reparo estructuras de madera "
        "ni equipos con partes eléctricas o motorizadas.",
    ),
    DemoProfile(
        "tapiceria-colonia", "Anahí Perdomo", "oficios", "Tapicería", "colonia-del-sacramento",
        "Retapizado de sillones y banquetas.",
        "Cambio tela, espuma y cinchas en sillones de uso doméstico. "
        "Retapizo respaldos acolchados y banquetas con la tela que elija el cliente. "
        "Mi trabajo se limita a la tapicería. No reparo estructuras ni soportes. Evalúo el acolchado, "
        "las costuras y los puntos de agarre "
        "antes de calcular la tela necesaria.",
    ),
    DemoProfile(
        "termicas-minas", "Joaquín Machado", "oficios", "Electricista", "minas",
        "Diagnóstico y mantenimiento de instalaciones eléctricas domiciliarias.",
        "Diagnostico por qué salta la térmica cuando se prenden dos aparatos a la vez. "
        "Reviso carga de los circuitos, disyuntores y llaves termomagnéticas en tableros domiciliarios. "
        "Puedo ubicar la línea que provoca el corte, identificar conexiones flojas y presupuestar "
        "la reparación del circuito. También reviso tomas que quedaron sin corriente tras un corte.",
    ),
    DemoProfile(
        "tableros-pando", "Melina Sas", "oficios", "Electricista", "pando",
        "Diagnóstico de cortes en viviendas y pequeños comercios.",
        "Reviso tableros eléctricos con disparos repetidos del interruptor o caídas de tensión al usar "
        "varios electrodomésticos. Separo el diagnóstico de la reparación, verifico qué circuito dispara "
        "la protección y cotizo el recambio necesario. También ordeno tableros existentes, identifico "
        "llaves y dejo un croquis sencillo de circuitos.",
    ),
    DemoProfile(
        "termicas-maldonado", "Renato Salgado", "oficios", "Electricidad domiciliaria", "maldonado",
        "Revisión de circuitos, diferencial y tableros domésticos.",
        "Atiendo viviendas donde baja la llave térmica al encender el horno y otro aparato. "
        "Compruebo el estado de la instalación, las borneras y los conductores en la zona del tablero. "
        "Trabajo con reposición de interruptores y revisión de tomas que calientan. "
        "Para edificios, coordino el acceso y las ventanas de trabajo con la administración.",
    ),
    DemoProfile(
        "termostatos-montevideo", "Cecilia Vela", "tecnologia", "Refrigeración", "montevideo",
        "Diagnóstico de heladeras y vitrinas refrigeradas.",
        "Cambio termostatos de heladeras y controlo el sensor cuando no corta el compresor. "
        "Reviso burletes y pérdidas de frío en vitrinas; limpio el desagüe interno si se junta agua. "
        "No reviso instalaciones eléctricas ni tableros de viviendas. El servicio se limita "
        "al equipo de refrigeración y su control de temperatura.",
    ),
    DemoProfile(
        "instala-luces-minas", "Emiliano Ramos", "oficios", "Iluminación decorativa", "minas",
        "Colocación de luminarias sobre circuitos existentes.",
        "Coloco lámparas colgantes, apliques de pared y tiras LED cuando ya está prevista la alimentación. "
        "Puedo reemplazar lámparas y montar perfiles de aluminio para iluminación de muebles. "
        "No reparo tableros, no cambio llaves térmicas y no atiendo cortes de corriente. "
        "Antes de la visita pido fotos del artefacto y de la superficie de montaje.",
    ),
    DemoProfile(
        "bomba-aljibe-minas", "Leonel Ribas", "servicios-rurales", "Mantenimiento de bombas", "minas",
        "Servicio a bombas domésticas y sistemas de captación de agua.",
        "Reparo bombas de aljibe que prenden pero dejaron de levantar agua. "
        "Reviso si entra aire por la aspiración y si perdió el cebado, pruebo la válvula de pie y compruebo "
        "la presión de salida. También reemplazo sellos dañados y recupero la alimentación del tanque. "
        "Coordino acceso al aljibe y aviso si hace falta retirar la bomba al taller.",
    ),
    DemoProfile(
        "bombas-mariscala", "Celina Cordero", "servicios-rurales", "Electromecánica de bombas", "mariscala",
        "Diagnóstico de bombas de agua para viviendas y huertas.",
        "Reparo bombas de agua domiciliarias que perdieron presión o se desceban después de apagarlas. "
        "Compruebo el presostato, el retén y la altura de aspiración. Hago pruebas de caudal en el taller "
        "y cambio accesorios gastados si se consiguen repuestos. Trabajo con bombas de superficie "
        "en aljibes y tanques de reserva.",
        ("Minas",),
    ),
    DemoProfile(
        "aljibes-tacuarembo", "Pablo Arismendi", "servicios-rurales", "Instalaciones de agua rural", "tacuarembo",
        "Sistemas de agua para casas de campo y predios pequeños.",
        "Hago diagnóstico y reparación de circuitos de bombeo de pozos y aljibes. "
        "Busco pérdidas ocultas en la manguera de aspiración y sustituyo válvulas que dejan caer "
        "la columna de agua. También inspecciono flotantes de tanques, ajusto tuberías y reinstalo "
        "bombas reparadas en taller.",
    ),
    DemoProfile(
        "limpieza-tanques-minas", "Guillermo Núñez", "hogar", "Limpieza de depósitos", "minas",
        "Limpieza programada de tanques y aljibes.",
        "Limpio tanques domiciliarios y retiro sedimentos de aljibes accesibles. "
        "Hago el vaciado y la limpieza interior y compruebo el cierre de la tapa. "
        "No reparo bombas ni fallas de presión. Si el problema está en el motor o la aspiración, "
        "pido que se atienda antes de programar el servicio de limpieza.",
    ),
    DemoProfile(
        "riego-durazno", "Antonia Cardona", "servicios-rurales", "Instalaciones de riego", "durazno",
        "Instalación de riego para viveros y huertas.",
        "Diseño y monto riego por goteo para huertas y viveros, con ajuste de programadores, filtros "
        "y emisores. Hago pruebas de distribución del agua y sustituyo tramos de manguera mordidos. "
        "Instalo bombas nuevas cuando el proyecto lo requiere. No reparo bombas en uso ni hago "
        "mantenimiento de aljibes domésticos.",
    ),
    DemoProfile(
        "catalogos-montevideo", "Lucía Menese", "eventos", "Fotografía de productos", "montevideo",
        "Sesiones de foto comercial para tiendas en línea.",
        "Hago fotografía de productos para catálogos y tiendas online, incluida mercadería pequeña "
        "que necesita varias vistas y colores consistentes. Puedo rehacer fotos que salieron oscuras "
        "o con reflejos, armar un fondo blanco y entregar formatos cuadrados para el catálogo. "
        "Coordino lotes de prendas, zapatos o accesorios y entrego archivos con nombres por producto.",
    ),
    DemoProfile(
        "productos-pando", "Alberto Repetto", "eventos", "Fotografía comercial", "pando",
        "Imágenes de producto para fichas de venta y campañas.",
        "Fotografío mercadería para catálogos digitales con iluminación pareja, fondo neutro "
        "y recorte limpio. Tomo vistas de frente y detalles de terminación; para objetos brillantes "
        "trabajo con luz difusa. Entrego las tomas en archivos livianos para la web y una copia "
        "de alta resolución para diseño o impresión.",
    ),
    DemoProfile(
        "fotos-menu-paysandu", "Javier Olmedo", "eventos", "Fotografía gastronómica", "paysandu",
        "Producción de imágenes para cartas y plataformas de pedidos.",
        "Hago fotos de platos, bebidas y productos envasados para catálogos de alimentos y tiendas online. "
        "Coordino horarios de cocina para fotografiar los platos recién hechos y selecciono fondos "
        "por línea de producto. Entrego versiones recortadas para menú y para aplicaciones de reparto. "
        "Trabajo en el local o con un lote corto en mi estudio.",
    ),
    DemoProfile(
        "eventos-montevideo", "Malena Seara", "eventos", "Fotografía de eventos", "montevideo",
        "Cobertura de reuniones, aniversarios y actos.",
        "Fotografío invitados, mesas y momentos destacados en cumpleaños y reuniones familiares. "
        "Coordino grupos para retratos y entrego una galería ordenada por momentos del evento. "
        "No hago fotografía de productos, mercadería ni sesiones para catálogos. "
        "Para cobertura nocturna puedo llevar iluminación portátil.",
    ),
    DemoProfile(
        "edicion-fotos-minas", "Adrián Fresnedo", "tecnologia", "Retoque fotográfico", "minas",
        "Edición digital de imágenes entregadas por el cliente.",
        "Corrijo color y elimino fondos para fichas de productos a partir de fotos existentes. "
        "Ajusto proporciones, exporto versiones para redes y puedo recuperar contraste de imágenes oscuras. "
        "No hago sesiones ni tomo fotos nuevas de mercadería. El cliente entrega los originales con "
        "la mayor resolución disponible.",
    ),
    DemoProfile(
        "paseos-minas", "Natalia Echevarría", "hogar", "Paseo y cuidado de perros", "minas",
        "Paseos de perros y visitas a domicilio durante viajes.",
        "Paseo perros todos los días mientras la familia está de viaje. "
        "Hago salidas individuales con correa y adapto la vuelta a perros mayores o que se asustan "
        "con el tránsito. En la visita puedo renovar agua y dejar comida medida según la rutina "
        "acordada. Aviso cuando termino la visita y si hubo algún cambio de comportamiento.",
    ),
    DemoProfile(
        "paseos-pando", "Sebastián Vigo", "hogar", "Paseador de mascotas", "pando",
        "Paseos individuales en recorridos de barrio.",
        "Saco a pasear perros al mediodía o al final de la tarde. Coordino el punto de encuentro "
        "y mantengo separados a perros reactivos. Ofrezco semanas completas de paseos para familias "
        "que viajan y quieren mantener la rutina del animal. También puedo hacer una visita breve "
        "para renovar agua entre salidas.",
    ),
    DemoProfile(
        "guarderia-salto", "Itatí Márquez", "hogar", "Guardería canina", "salto",
        "Estadías de perros de familias que viajan.",
        "Recibo perros en una guardería doméstica con grupos pequeños y patios separados. "
        "Mantengo los horarios de comida y descanso que indica cada familia. "
        "No hago paseos de perros a domicilio ni retiro mascotas en otras ciudades. "
        "Ofrezco un encuentro previo para ver si el animal se adapta al espacio.",
    ),
    DemoProfile(
        "visitas-gatos-rocha", "Elisa Marrero", "hogar", "Cuidado de gatos", "rocha",
        "Visitas para gatos durante ausencias cortas.",
        "Paso por la casa para renovar agua, repartir las porciones y limpiar el arenero. "
        "Mantengo ventanas y accesos según la indicación de la familia y mando un aviso después "
        "de cada visita. Estoy especializada en gatos con rutinas tranquilas. No ofrezco paseos "
        "de perros ni hospedo animales fuera de su casa.",
    ),
    DemoProfile(
        "peluqueria-canina-minas", "Mariano Soto", "hogar", "Peluquería canina", "minas",
        "Baño, desenredado y arreglo de pelo canino.",
        "Baño y seco perros por turno, con cepillado y desenredado según el manto. "
        "Puedo recortar alrededor de las patas y limpiar la zona exterior de las orejas. "
        "No hago paseos ni guardería de perros. El perro llega con su persona y se retira al terminar.",
    ),
    DemoProfile(
        "mecanico-minas", "Gustavo Malán", "oficios", "Mecánico automotor", "minas",
        "Diagnóstico y mecánica general de autos y utilitarios livianos.",
        "Reparo frenos que vibran o hacen ruido, sustituyo amortiguadores y reviso tren delantero. "
        "Diagnostico fallas de arranque, motores que se apagan en frío y pérdidas de refrigerante. "
        "Hago mantenimiento periódico con cambio de aceite, filtros y correa de accesorios. "
        "Confirmo qué repuestos necesita el auto después de revisar la falla en el taller.",
    ),
    DemoProfile(
        "mecanico-solis", "Marcela Abreu", "oficios", "Mecánica automotriz", "solis-de-mataojo",
        "Mantenimiento y reparación de autos y camionetas a nafta.",
        "Atiendo autos que dan arranque pero no prenden, embragues que patinan y frenos con desgaste. "
        "Busco la causa de ruidos en la suspensión y reviso radiadores que pierden refrigerante. "
        "También hago cambios de aceite y filtros, ajusto correas y pruebo batería y alternador. "
        "Trabajo con vehículos livianos y coordino la recepción en el taller.",
    ),
    DemoProfile(
        "mecanico-balneario-solis", "Silvia Queirolo", "oficios", "Mecánica automotriz", "balneario-solis",
        "Revisión y reparación de autos livianos para uso cotidiano.",
        "Reviso autos que se recalientan, pierden líquido o encienden la luz de batería. "
        "Compruebo el circuito de refrigeración y diagnostico fallas eléctricas de arranque. "
        "También cambio pastillas de freno, limpio contactos corroídos y hago mantenimiento por kilometraje. "
        "Atiendo vehículos en el taller y coordino el ingreso fuera de fines de semana largos.",
    ),
    DemoProfile(
        "notebooks-fray-bentos", "Brenda Rivas", "tecnologia", "Reparación de computadoras", "fray-bentos",
        "Diagnóstico de portátiles que se apagan o calientan.",
        "Reviso notebooks que se apagan mientras están cargando o fallan al abrir programas pesados. "
        "Pruebo el cargador, compruebo ventilación y temperatura y reviso el estado del disco. "
        "Puedo sustituir un ventilador ruidoso, instalar almacenamiento compatible y reinstalar "
        "programas después de respaldar los archivos acordados.",
    ),
    DemoProfile(
        "extraccion-datos-florida", "Mauro Corbo", "tecnologia", "Recuperación de datos", "florida",
        "Rescate de archivos de discos y memorias extraíbles.",
        "Recupero carpetas de discos externos que dejaron de abrir y fotos de tarjetas de memoria "
        "tras un borrado accidental. Trabajo con una copia del soporte cuando se puede leer. "
        "Entrego los archivos recuperados en un dispositivo aparte. No reemplazo pantallas "
        "ni arreglo equipos que no encienden.",
    ),
    DemoProfile(
        "redes-rivera", "Ramiro Soria", "tecnologia", "Redes domésticas", "rivera",
        "Diagnóstico de wifi débil y cableado de red.",
        "Reviso conexiones que se cortan al pasar de una habitación a otra y ubico zonas "
        "de mala cobertura de wifi. Configuro puntos de acceso, sustituyo fichas de red "
        "rotas y separo dispositivos de visita de los equipos de trabajo. "
        "Dejo identificados el router y los cables que quedaron instalados.",
    ),
    DemoProfile(
        "humedad-trinidad", "Paula Etcheverry", "oficios", "Reparación de humedad", "trinidad",
        "Diagnóstico de humedades en muros interiores.",
        "Reviso manchas, pintura inflada y revoque suelto en paredes cerca del suelo. "
        "Distingo filtraciones visibles de señales de condensación y preparo un presupuesto "
        "para reparar el revoque después de atender la causa. Hago terminaciones de interior "
        "en áreas chicas y verifico el secado antes de pintar.",
    ),
    DemoProfile(
        "bicicletas-mercedes", "Fabián Ocampo", "oficios", "Mecánica de bicicletas", "mercedes",
        "Frenos, cambios y ruedas de bicicletas urbanas.",
        "Reparo bicicletas cuya cadena salta al subir una cuesta o cuyo freno roza la rueda. "
        "Cambio cables, ajusto cambios y reviso rayos flojos y rodamientos. "
        "También arreglo cámaras pinchadas y sustituyo cubiertas partidas. "
        "No trabajo con la batería ni la electrónica de bicicletas asistidas.",
    ),
    DemoProfile(
        "persianas-artigas", "Leticia Vera", "oficios", "Reparación de persianas", "artigas",
        "Arreglo de persianas manuales de enrollar.",
        "Reparo persianas de cinta que quedaron trabadas a media altura, cambiando la cinta "
        "o la polea si se cortaron. Reviso lamas desplazadas, topes y soportes del eje. "
        "Puedo retirar el cajón para limpiar la guía cuando tiene restos de pintura. "
        "Para persianas motorizadas alcanzo solo la parte mecánica.",
    ),
    DemoProfile(
        "costura-carmelo", "Ester Noriega", "oficios", "Arreglos de costura", "carmelo",
        "Ajustes de prendas, cierres y dobladillos.",
        "Cambio cierres de camperas y ajusto dobladillos cuando un pantalón arrastra. "
        "Refuerzo costuras abiertas en los bolsillos y hago pequeños ajustes para que una prenda "
        "se pueda seguir usando. La primera prueba sirve para acordar el largo y marcar el punto "
        "exacto donde hay que reforzar.",
    ),
    DemoProfile(
        "subtitulos-melo", "Florencia Otero", "profesionales", "Transcripción y subtítulos", "melo",
        "Subtitulado en español de entrevistas y videos breves.",
        "Transcribo entrevistas, distingo las voces y marco nombres que necesitan confirmación. "
        "Preparo subtítulos con tiempos sincronizados para videos cortos, clases grabadas y "
        "presentaciones. Acordamos el estilo de lectura y entrego una versión editable "
        "con los pasajes de audio que quedaron dudosos.",
    ),
    DemoProfile(
        "apoyo-lectura-treinta-y-tres", "Noemí Ardao", "educacion", "Apoyo escolar", "treinta-y-tres",
        "Acompañamiento en lectura y escritura para escolares.",
        "Doy apoyo en comprensión lectora a escolares que leen un texto pero les cuesta contarlo "
        "con sus palabras. Practicamos con cuentos cortos, preguntas simples y resúmenes pequeños. "
        "También organizo una rutina de estudio y adapto los materiales a lo que trabajan en clase.",
    ),
    DemoProfile(
        "masaje-maldonado", "Verónica Casas", "bienestar-y-salud", "Masajes de bienestar", "maldonado",
        "Sesiones de relajación y descanso.",
        "Ofrezco masajes de bienestar para quienes buscan un momento de descanso luego de una semana "
        "de trabajo. Acordamos qué áreas trabajar y qué presión resulta cómoda durante la sesión. "
        "También propongo pausas y cambios de postura si el cliente necesita estar más cómodo. "
        "El servicio es de relajación.",
    ),
    DemoProfile(
        "respiracion-rocha", "Matilde De León", "espiritualidad", "Prácticas de meditación", "rocha",
        "Encuentros de respiración suave y meditación guiada.",
        "Guío encuentros breves de meditación para gente que está empezando y prefiere practicar sentada. "
        "Hacemos una pausa, respiración tranquila y ejercicios sencillos de atención. "
        "Podemos trabajar de forma individual o en grupos reducidos y ajustar la duración al ritmo de cada persona.",
    ),
    DemoProfile(
        "barberia-durazno", "Rodrigo Ayala", "belleza", "Barbería", "durazno",
        "Corte, perfilado y arreglo de barba.",
        "Hago cortes con tijera o máquina según la textura del pelo, y prolijo barba sin cambiar "
        "el largo general cuando la persona lo pide. Puedo corregir bordes desparejos de un corte previo. "
        "Coordinamos el estilo y el mantenimiento deseado antes de empezar.",
    ),
)


def _refresh_legacy_copy():
    replacements = {row.profile_id: row for row in PROFILES if row.key in _LEGACY_COPY}
    profiles = db.session.scalars(select(Profile).where(
        Profile.id.in_(replacements),
        Profile.is_demo_fixture.is_(True),
        Profile.created_at == _CREATED_AT,
        Profile.updated_at == _CREATED_AT,
    )).all()
    corrected = 0
    try:
        for profile in profiles:
            row = replacements[profile.id]
            seeded_fields = {
                "owner_id": row.owner_id,
                "slug": row.profile_id,
                "display_name": f"{row.name} Demo",
                "category_id": row.category,
                "profession": row.profession,
                "locality_id": row.locality,
                "service_area": list(row.coverage),
                "tags": [row.profession],
                "status": "active" if row.active else "inactive",
            }
            if any(getattr(profile, key) != value for key, value in seeded_fields.items()):
                continue
            old_copy = f"{profile.short_description}\n{profile.description}"
            if hashlib.sha256(old_copy.encode("utf-8")).hexdigest() != _LEGACY_COPY[row.key]:
                continue

            # Keep a concurrent profile edit even if it happened after the fingerprint check.
            changed = db.session.execute(update(Profile).where(
                Profile.id == row.profile_id,
                Profile.owner_id == row.owner_id,
                Profile.updated_at == _CREATED_AT,
                Profile.short_description == profile.short_description,
                Profile.description == profile.description,
            ).values(
                short_description=row.summary,
                description=row.description + _DESCRIPTION_SUFFIX,
                updated_at=utcnow(),
            ).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                continue
            db.session.refresh(profile)
            update_search_text(profile)
            sync_profile_search(profile)
            corrected += 1
        if corrected:
            db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return corrected


def seed_rich_search_profiles():
    """Seed missing demo data once and refresh untouched legacy fixture copy."""
    skipped = {"skipped": True, "profiles": 0, "active": 0}
    if db.session.get(SeedState, SEED_KEY):
        corrected = _refresh_legacy_copy()
        return {**skipped, "updated": corrected} if corrected else skipped

    category_ids = {item.id for item in db.session.scalars(select(Category)).all()}
    departments_by_locality = dict(db.session.execute(select(Locality.id, Locality.department_id)).all())
    if any(row.category not in category_ids or row.locality not in departments_by_locality for row in PROFILES):
        raise RuntimeError("Faltan categorías o localidades para los perfiles ficticios de búsqueda.")

    profile_ids = {row.profile_id for row in PROFILES}
    owner_ids = {row.owner_id for row in PROFILES}
    try:
        # Reservar la marca antes de escribir perfiles evita sembrar dos veces en paralelo.
        db.session.add(SeedState(key=SEED_KEY, value="applied"))
        db.session.flush()
        if (db.session.scalar(select(Profile.id).where(
                or_(Profile.id.in_(profile_ids), Profile.slug.in_(profile_ids))
            ).limit(1)) or db.session.scalar(select(Account.id).where(Account.id.in_(owner_ids)).limit(1))):
            raise RuntimeError("Ya existe un ID o slug reservado para los perfiles ficticios de búsqueda.")

        for row in PROFILES:
            display_name = f"{row.name} Demo"
            account = Account(id=row.owner_id, display_name=display_name)
            profile = Profile(
                id=row.profile_id, slug=row.profile_id, owner=account, display_name=display_name,
                category_id=row.category, profession=row.profession, profession_normalized=normalize(row.profession),
                department_id=departments_by_locality[row.locality], locality_id=row.locality,
                short_description=row.summary, description=row.description + _DESCRIPTION_SUFFIX,
                service_area=list(row.coverage), tags=[row.profession], is_demo_fixture=True,
                status="active" if row.active else "inactive", created_at=_CREATED_AT, updated_at=_CREATED_AT,
            )
            update_search_text(profile)
            db.session.add(profile)
            sync_profile_search(profile)
            if row.coverage:
                resolve_coverage_values(profile.id, profile.service_area)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if db.session.get(SeedState, SEED_KEY):
            return skipped
        raise
    except Exception:
        db.session.rollback()
        raise

    return {"skipped": False, "profiles": len(PROFILES), "active": sum(row.active for row in PROFILES)}
