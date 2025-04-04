from sqlalchemy import Column, Integer, String, ForeignKey, Time
from sqlalchemy.orm import relationship
from database import Base

class Agency(Base):
    __tablename__ = 'agencies'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    # Relationships
    wraparound_services = relationship("WraparoundService", back_populates="agency")
    cultural_populations = relationship("CultureServed", back_populates="agency")

class WraparoundService(Base):
    __tablename__ = 'wraparound_services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_id = Column(String, ForeignKey('agencies.id'))
    service = Column(String)

    agency = relationship("Agency", back_populates="wraparound_services")

class CultureServed(Base):
    __tablename__ = 'cultures_served'
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_id = Column(String, ForeignKey('agencies.id'))
    culture = Column(String)

    agency = relationship("Agency", back_populates="cultural_populations")

class DistributionSite(Base):
    __tablename__ = 'distribution_sites'
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_id = Column(String, ForeignKey('agencies.id'))
    shipping_address = Column(String)
    day_of_week = Column(String)
    start_time = Column(Time)
    end_time = Column(Time)
    food_format = Column(String)
    distribution_model = Column(String)

    agency = relationship("Agency")
