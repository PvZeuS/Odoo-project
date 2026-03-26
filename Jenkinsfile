pipeline {
    agent any

    environment {
        EC2_USER     = 'ubuntu'
        EC2_IP       = branchIP()
        REMOTE_DIR   = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        
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
                        echo "Desplegando rama ${BRANCH_NAME} en la IP ${EC2_IP}:${ODOO_PORT}..."
                        
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
                            
                            docker compose up -d --build --remove-orphans
                            
                            echo "Esperando estabilidad de los servicios..."
                            sleep 15
                            
                            # Actualización de todos los módulos encontrados en addons
                            docker compose run --rm odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init
                            
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
    // Retorna la IP de Main para la rama principal, de lo contrario Staging
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101'
}

def branchPort() {
    // Retorna 8071 para Main, 8070 para Staging/otros
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070'
}