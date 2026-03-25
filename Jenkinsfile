pipeline {
    agent any

    environment {
        EC2_USER     = 'ubuntu'
        EC2_IP       = branchIP()
        REMOTE_DIR   = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        
        // Formateo de nombres para evitar caracteres inválidos en Docker
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        ODOO_PORT            = branchPort()
        POSTGRES_DB          = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        POSTGRES_USER        = 'odoo'
        POSTGRES_PASSWORD    = credentials('odoo-db-password')
    }

    stages {
        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) {
                    sh '''
                        echo "Desplegando rama ${BRANCH_NAME} en la IP ${EC2_IP}..."
                        
                        # Crear directorio y subir archivos
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        # Ejecución de comandos remotos usando Docker Compose V2
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            
                            # Exportar variables para docker compose
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
                            
                            # 1. Levantar servicios (Comando moderno sin guion)
                            docker compose up -d --build --remove-orphans
                            
                            echo "Esperando estabilidad de los servicios..."
                            sleep 15
                            
                            # 2. ACTUALIZACIÓN DE DB
                            # Usamos 'run --rm' para evitar conflictos de puerto 8069
                            docker compose run --rm odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init
                            
                            # 3. Reiniciar el servicio principal para aplicar cambios
                            docker compose restart odoo
EOF
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "¡Despliegue Exitoso! Disponible en: http://${EC2_IP}:${ODOO_PORT}"
        }
        failure {
            echo "El despliegue ha fallado. Revisa los logs de la consola de Jenkins."
        }
    }
}

def branchIP() {
    switch (env.BRANCH_NAME) {
        case 'main':    return '3.144.231.64'
        case 'staging': return '18.219.33.101'
        default:        return '18.219.33.101'
    }
}

def branchPort() {
    switch (env.BRANCH_NAME) {
        case 'main':    return '8071'
        case 'staging': return '8070'
        default:        return '8069'
    }
}