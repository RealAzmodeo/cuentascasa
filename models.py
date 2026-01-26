from sqlalchemy import Column, Integer, String, Float, Date, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, index=True)
    monto = Column(Float, nullable=False)
    categoria = Column(String(100), nullable=False, index=True)
    subcategoria = Column(String(100))
    detalle = Column(String(500))
    tipo = Column(String(20), nullable=False) # Gasto / Ingreso
    tienda = Column(String(255))
    cuenta = Column(String(100), nullable=False, index=True)
    saldo_banco = Column(Float)
    link_id = Column(String(100), index=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "monto": self.monto,
            "categoria": self.categoria,
            "subcategoria": self.subcategoria,
            "detalle": self.detalle,
            "tipo": self.tipo,
            "tienda": self.tienda,
            "cuenta": self.cuenta,
            "link_id": self.link_id
        }
