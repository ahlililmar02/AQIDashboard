## About This Project

This platform compiles real-time and historical air quality data for Jakarta from four independent API sources. The idea is so that users can explore and download the complete dataset for their own analysis or projects. Beyond station measurements, the platform predicts PM2.5 concentrations for any latitude–longitude coordinate in Jakarta, providing estimates in areas without direct monitoring coverage.

## Technical Overview
- **Data Processing**: Compile and process PM2.5 data from multiple APIs using Python.  
- **Database**: Store and query data efficiently with PostgreSQL.  
- **Deployment**: Containerized with Docker and deployed on Ubuntu server.  
- **Frontend**: Built with Streamlit, custom UI components, and assets.  
- **Machine Learning**: Run models locally, then upload results to the database.  
- **Serving**: Optimized with NGINX for performance and reliability.  

## References
- Xue, T., Zheng, Y., Geng, G., Zheng, B., Jiang, X., Zhang, Q., & He, K. *Fusing Observational, Satellite Remote Sensing and Air Quality Model Simulated Data to Estimate Spatiotemporal Variations of PM2.5 Exposure in China.*  
- Paciorek, C. J., et al. (2008). *Spatiotemporal associations between satellite-derived aerosol optical depth and PM2.5 in the eastern United States.*  
- **Data Sources**:  
  - IQAir Jakarta  
  - Jakarta Rendah Emisi  
  - Kementerian Lingkungan Hidup dan Kehutanan (KLHK)  
  - Udara Jakarta  
  - ERA5 (ECMWF Reanalysis v5)  
  - Google Earth Engine  
